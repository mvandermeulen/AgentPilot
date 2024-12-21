
import json
import logging
import os

import requests
import keyring
from PySide6.QtCore import QRunnable, Signal, Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import *

from src.gui.config import ConfigPages, ConfigFields, ConfigDBTree, ConfigTabs, \
    ConfigJoined, ConfigJsonTree, get_widget_value, CHBoxLayout, \
    ConfigPlugin, ConfigExtTree, ConfigWidget, ConfigAsyncWidget

from src.gui.pages.blocks import Page_Block_Settings
from src.gui.pages.modules import Page_Module_Settings
from src.gui.pages.schedule import Page_Schedule_Settings
from src.gui.pages.tools import Page_Tool_Settings
from src.system.environments import EnvironmentSettings

from src.utils import sql
from src.gui.widgets import IconButton, find_main_widget
from src.utils.helpers import display_messagebox, block_signals, block_pin_mode

from src.plugins.openaiassistant.modules.settings_plugin import Page_Settings_OAI

from src.gui.pages.models import Page_Models_Settings
from src.utils.reset import reset_application


class Page_Settings(ConfigPages):
    def __init__(self, parent):
        super().__init__(parent=parent)
        self.main = parent
        self.icon_path = ":/resources/icon-settings.png"

        self.try_add_breadcrumb_widget()
        self.breadcrumb_text = 'Settings'
        self.include_in_breadcrumbs = True

        self.locked_above = ['System', 'Display', 'Models', 'Blocks', 'Roles', 'Tools', 'Envs', 'Modules', 'Plugins']
        self.locked_below = []
        self.pages = {
            'System': self.Page_System_Settings(self),
            'Display': self.Page_Display_Settings(self),
            # 'Defaults': self.Page_Default_Settings(self),
            'Models': Page_Models_Settings(self),
            'Blocks': Page_Block_Settings(self),
            'Roles': self.Page_Role_Settings(self),
            'Tools': Page_Tool_Settings(self),
            # 'Files': self.Page_Files_Settings(self),
            'Envs': self.Page_Environments_Settings(self),
            'Modules': Page_Module_Settings(self),
            # 'Sets': self.Page_Sets_Settings(self),
            # 'VecDB': self.Page_VecDB_Settings(self),
            # 'Spaces': self.Page_Workspace_Settings(self),
            'Plugins': self.Page_Plugin_Settings(self),
            # 'Schedule': Page_Schedule_Settings(self),
            # 'Matrix': self.Page_Matrix_Settings(self),
            # 'Sandbox': self.Page_Role_Settings(self),
            # "Vector DB": self.Page_Role_Settings(self),
            # 'Portfolio': self.Page_Portfolio_Settings(self),
        }
        # custom_pages =
        # self.pinnable_pages = ['Blocks', 'Tools', 'Modules']
        self.is_pin_transmitter = True

    def save_config(self):
        """Saves the config to database when modified"""
        json_config = json.dumps(self.get_config())
        sql.execute("UPDATE `settings` SET `value` = ? WHERE `field` = 'app_config'", (json_config,))
        self.main.system.config.load()
        system_config = self.main.system.config.dict
        self.load_config(system_config)

    def build_schema(self):
        self.build_custom_pages()
        # super().build_schema()
        self.build_schema_temp()

    def build_custom_pages(self):
        # rebuild self.pages efficiently with custom pages inbetween locked pages
        from src.gui.main import get_page_definitions
        page_definitions = get_page_definitions()
        new_pages = {}
        for page_name in self.locked_above:
            new_pages[page_name] = self.pages[page_name]
        for page_name, page_class in page_definitions.items():
            try:
                new_pages[page_name] = page_class(parent=self)
            except Exception as e:
                display_messagebox(
                    icon=QMessageBox.Warning,
                    title="Error loading page",
                    text=f"Error loading page '{page_name}': {e}",
                    buttons=QMessageBox.Ok
                )
        for page_name in self.locked_below:
            new_pages[page_name] = self.pages[page_name]
        self.pages = new_pages
        # self.build_schema()

    def build_schema_temp(self):  # todo unify mechanism with main menu
        """OVERRIDE DEFAULT. Build the widgets of all pages from `self.pages`"""
        # remove all widgets from the content stack except for locked pages
        for i in reversed(range(self.content.count())):
            remove_widget = self.content.widget(i)
            if remove_widget in self.pages.values():
                continue
            self.content.removeWidget(remove_widget)
            remove_widget.deleteLater()

        # wid_Cnt = self.content.count()
        # if wid_Cnt > 0:
        #     pass

        # remove settings sidebar
        if getattr(self, 'settings_sidebar', None):
            self.layout.removeWidget(self.settings_sidebar)
            self.settings_sidebar.deleteLater()

        # if getattr(self, 'settings_sidebar', None):
        #     self.settings_sidebar.load()

        # hidden_pages = getattr(self, 'hidden_pages', [])  # !! #

        with block_signals(self.content, recurse_children=False):
            for i, (page_name, page) in enumerate(self.pages.items()):
                # if page_name in hidden_pages:  # !! #
                #     continue
                widget = self.content.widget(i)
                if widget != page:
                    self.content.insertWidget(i, page)
                    if hasattr(page, 'build_schema'):
                        page.build_schema()

            if self.default_page:
                default_page = self.pages.get(self.default_page)
                page_index = self.content.indexOf(default_page)
                self.content.setCurrentIndex(page_index)

        self.settings_sidebar = self.ConfigSidebarWidget(parent=self)
        # self.settings_sidebar.setFixedWidth(70)
        # self.settings_sidebar.setContentsMargins(4,0,0,4)

        layout = CHBoxLayout()
        if not self.right_to_left:
            layout.addWidget(self.settings_sidebar)
            layout.addWidget(self.content)
        else:
            layout.addWidget(self.content)
            layout.addWidget(self.settings_sidebar)

        # # last_item = self.layout.takeAt(self.layout.count() - 1)  # todo why is it working without?
        # is_a_layout = isinstance(last_item, CHBoxLayout)
        # if last_item and is_a_layout:
        #     #

        self.layout.addLayout(layout)

    # def build_schema(self):
    #     """Build the widgets of all pages from `self.pages`"""
    #     # self.blockSignals(True)
    #     # remove all widgets from the content stack
    #     for i in reversed(range(self.content.count())):
    #         remove_widget = self.content.widget(i)
    #         self.content.removeWidget(remove_widget)
    #         remove_widget.deleteLater()
    #
    #     # remove settings sidebar
    #     if getattr(self, 'settings_sidebar', None):
    #         self.layout.removeWidget(self.settings_sidebar)
    #         self.settings_sidebar.deleteLater()
    #
    #     # hidden_pages = getattr(self, 'hidden_pages', [])  # !! #
    #     pass
    #     with block_signals(self.content, recurse_children=False):
    #         for page_name, page in self.pages.items():
    #             # if page_name in hidden_pages:  # !! #
    #             #     continue
    #
    #             if hasattr(page, 'build_schema'):
    #                 page.build_schema()
    #             self.content.addWidget(page)
    #
    #         if self.default_page:
    #             default_page = self.pages.get(self.default_page)
    #             page_index = self.content.indexOf(default_page)
    #             self.content.setCurrentIndex(page_index)
    #
    #
    #     self.settings_sidebar = self.ConfigSidebarWidget(parent=self)
    #
    #     layout = CHBoxLayout()
    #     if not self.right_to_left:
    #         layout.addWidget(self.settings_sidebar)
    #         layout.addWidget(self.content)
    #     else:
    #         layout.addWidget(self.content)
    #         layout.addWidget(self.settings_sidebar)
    #
    #     self.layout.addLayout(layout)
    # def build_schema_temp(self):  # todo unify mechanism with main menu
    #     """OVERRIDE DEFAULT. Build the widgets of all pages from `self.pages`"""
    #     # remove all widgets from the content stack except for locked pages
    #     for i in reversed(range(self.content.count())):
    #         remove_widget = self.content.widget(i)
    #         if remove_widget in self.pages.values():
    #             continue
    #         self.content.removeWidget(remove_widget)
    #         remove_widget.deleteLater()
    #
    #     # wid_Cnt = self.content.count()
    #     # if wid_Cnt > 0:
    #     #     pass
    #
    #     # remove settings sidebar
    #     if getattr(self, 'settings_sidebar', None):
    #         self.layout.removeWidget(self.settings_sidebar)
    #         self.settings_sidebar.deleteLater()
    #
    #     # if getattr(self, 'settings_sidebar', None):
    #     #     self.settings_sidebar.load()
    #
    #     # hidden_pages = getattr(self, 'hidden_pages', [])  # !! #
    #
    #     # with block_signals(self):
    #     for i, (page_name, page) in enumerate(self.pages.items()):
    #         # if page_name in hidden_pages:  # !! #
    #         #     continue
    #         widget = self.content.widget(i)
    #         if widget != page:
    #             self.content.insertWidget(i, page)
    #             if hasattr(page, 'build_schema'):
    #                 page.build_schema()
    #
    #     self.settings_sidebar = self.ConfigSidebarWidget(parent=self)
    #     self.settings_sidebar.setFixedWidth(70)
    #     self.settings_sidebar.setContentsMargins(4,0,0,4)
    #
    #     layout = CHBoxLayout()
    #     if not self.right_to_left:
    #         layout.addWidget(self.settings_sidebar)
    #         layout.addWidget(self.content)
    #     else:
    #         layout.addWidget(self.content)
    #         layout.addWidget(self.settings_sidebar)
    #
    #     last_layout = self.layout.takeAt(self.layout.count() - 1)
    #     if last_layout:
    #         del last_layout
    #
    #     self.layout.addLayout(layout)

    class Page_System_Settings(ConfigJoined):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.main = parent.main
            self.widgets = [
                self.Page_System_Login(parent=self),
                self.Page_System_Fields(parent=self),
            ]

        class Page_System_Login(ConfigAsyncWidget):
            fetched_logged_in_user = Signal(str)

            def __init__(self, parent):
                super().__init__(parent=parent)
                self.fetched_logged_in_user.connect(self.load_user, Qt.QueuedConnection)
                self.layout = QHBoxLayout(self)

                self.lbl_username = QLabel('username')
                self.lbl_username.hide()
                # self.lbl_password = QLabel('Password')
                self.username = QLineEdit()
                self.username.setPlaceholderText('Username')
                self.username.setFixedWidth(150)
                self.password = QLineEdit()
                self.password.setPlaceholderText('Password')
                self.password.setFixedWidth(150)
                self.password.setEchoMode(QLineEdit.EchoMode.Password)

                self.login_button = QPushButton('Login')
                self.login_button.setFixedWidth(100)
                self.login_button.clicked.connect(self.login)

                self.logout_button = QPushButton('Logout')
                self.logout_button.setFixedWidth(100)
                self.logout_button.clicked.connect(self.logout)
                self.logout_button.hide()
                # self.logout_button.clicked.connect(self.logout)

                self.layout.addWidget(self.lbl_username)
                self.layout.addWidget(self.username)
                self.layout.addWidget(self.password)
                self.layout.addWidget(self.login_button)
                self.layout.addWidget(self.logout_button)
                self.layout.addStretch(1)

                self.load()

            # def load(self):

            class LoadRunnable(QRunnable):
                def __init__(self, parent):
                    super().__init__()
                    self.parent = parent

                def run(self):
                    token = keyring.get_password("agentpilot", "user")
                    user = self.parent.validate_user(token)
                    self.parent.fetched_logged_in_user.emit(user)

            def validate_user(self, token):
                url = "https://agentpilot.ai/api/auth.php"
                data = {
                    'action': 'validate',
                    'token': token
                }
                try:
                    response = requests.post(url, data=data)
                    response.raise_for_status()  # Raises an HTTPError for bad responses
                    result = response.json()
                except requests.RequestException as e:
                    result = {"success": False, "message": f"Request failed: {str(e)}"}

                if not result.get('success', False) or 'username' not in result:
                    return None

                return result['username']

            @Slot(str)
            def load_user(self, user):
                logged_in = user is not None
                if logged_in:
                    self.username.setVisible(False)
                    self.password.setVisible(False)
                    self.login_button.setVisible(False)
                    self.logout_button.setVisible(True)
                    self.lbl_username.setVisible(True)
                    self.lbl_username.setText(f'Logged in as: {user}')
                else:
                    self.logout_button.setVisible(False)
                    self.lbl_username.setVisible(False)
                    self.username.setVisible(True)
                    self.password.setVisible(True)
                    self.login_button.setVisible(True)

            def login(self):
                username = self.username.text()
                password = self.password.text()
                url = "https://agentpilot.ai/api/auth.php"

                if not username or not password:
                    raise ValueError("Username and password are required")
                data = {
                    'action': 'login',
                    'username': username,
                    'password': password
                }

                try:
                    response = requests.post(url, data=data)
                    response.raise_for_status()  # Raises an HTTPError for bad responses
                    result = response.json()
                except requests.RequestException as e:
                    result = {"success": False, "message": f"Request failed: {str(e)}"}

                if not result.get('success', False) or 'token' not in result:
                    display_messagebox(
                        icon=QMessageBox.Warning,
                        text=result.get('message', 'Login failed'),
                        title='Error',
                    )
                    return

                token = result['token']
                keyring.set_password("agentpilot", "user", token)
                self.load()

            def logout(self):
                keyring.delete_password("agentpilot", "user")
                self.load()

        class Page_System_Fields(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.parent = parent
                self.main = parent.main
                self.label_width = 145
                self.margin_left = 20
                self.conf_namespace = 'system'
                self.schema = [
                    {
                        'text': 'Language',
                        'type': 'LanguageComboBox',
                        'default': 'en',
                    },
                    {
                        'text': 'Dev mode',
                        'type': bool,
                        'default': False,
                    },
                    {
                        'text': 'Telemetry',
                        'type': bool,
                        'default': True,
                    },
                    {
                        'text': 'Always on top',
                        'type': bool,
                        'default': True,
                    },
                    {
                        'text': 'Auto-run tools',
                        'type': int,
                        'minimum': 0,
                        'maximum': 30,
                        'step': 1,
                        'default': 5,
                        'label_width': 165,
                        'has_toggle': True,
                    },
                    {
                        'text': 'Auto-run code',
                        'type': int,
                        'minimum': 0,
                        'maximum': 30,
                        'step': 1,
                        'default': 5,
                        'label_width': 165,
                        'tooltip': 'Auto-run code messages (where role = code)',
                        'has_toggle': True,
                    },
                    {
                        'text': 'Auto-complete',
                        'type': bool,
                        'width': 40,
                        'tooltip': 'This is not an AI completion, it''s a statistical approach to quickly add commonly used phrases',
                        'default': True,
                    },
                    {
                        'text': 'Voice input method',
                        'type': ('None',),
                        'default': 'None',
                    },
                    {
                        'text': 'Default chat model',
                        'type': 'ModelComboBox',
                        'default': 'mistral/mistral-large-latest',
                    },
                    {
                        'text': 'Auto title',
                        'type': bool,
                        'width': 40,
                        'default': True,
                        'row_key': 0,
                    },
                    {
                        'text': 'Auto-title model',
                        'label_position': None,
                        'type': 'ModelComboBox',
                        'default': 'mistral/mistral-large-latest',
                        'row_key': 0,
                    },
                    {
                        'text': 'Auto-title prompt',
                        'type': str,
                        'default': 'Generate a brief and concise title for a chat that begins with the following message:\n\n{user_msg}',
                        'num_lines': 5,
                        'label_position': 'top',
                        'stretch_x': True,
                    },
                ]

            def after_init(self):
                self.dev_mode.stateChanged.connect(lambda state: self.toggle_dev_mode(state))
                self.always_on_top.stateChanged.connect(self.main.toggle_always_on_top)

                # add a button 'Reset database'
                self.reset_app_btn = QPushButton('Reset Application')
                self.reset_app_btn.clicked.connect(reset_application)
                self.layout.addWidget(self.reset_app_btn)

            def toggle_dev_mode(self, state=None):
                # pass
                if state is None and hasattr(self, 'dev_mode'):
                    state = self.dev_mode.isChecked()

                self.main.page_chat.top_bar.btn_info.setVisible(state)
                self.main.page_settings.pages['System'].widgets[1].reset_app_btn.setVisible(state)

                for config_pages in self.main.findChildren(ConfigPages):
                    for page_name, page in config_pages.pages.items():
                        page_is_dev_mode = getattr(page, 'IS_DEV_MODE', False)
                        if not page_is_dev_mode:
                            continue
                        config_pages.settings_sidebar.page_buttons[page_name].setVisible(state)

                self.main.apply_stylesheet()

    class Page_Display_Settings(ConfigJoined):
        def __init__(self, parent):
            super().__init__(parent=parent)

            self.conf_namespace = 'display'
            button_layout = CHBoxLayout()
            self.btn_delete_theme = IconButton(
                parent=self,
                icon_path=':/resources/icon-minus.png',
                tooltip='Delete theme',
                size=18,
            )
            self.btn_save_theme = IconButton(
                parent=self,
                icon_path=':/resources/icon-save.png',
                tooltip='Save current theme',
                size=18,
            )
            button_layout.addWidget(self.btn_delete_theme)
            button_layout.addWidget(self.btn_save_theme)
            button_layout.addStretch(1)
            self.layout.addLayout(button_layout)
            self.btn_save_theme.clicked.connect(self.save_theme)
            self.btn_delete_theme.clicked.connect(self.delete_theme)

            self.widgets = [
                self.Page_Display_Themes(parent=self),
                self.Page_Display_Fields(parent=self),
            ]
            self.add_stretch_to_end = True

        def save_theme(self):
            current_config = self.get_current_display_config()
            current_config_str = json.dumps(current_config, sort_keys=True)
            theme_exists = sql.get_scalar("""
                SELECT COUNT(*)
                FROM themes
                WHERE config = ?
            """, (current_config_str,))
            if theme_exists:
                display_messagebox(
                    icon=QMessageBox.Warning,
                    text='Theme already exists',
                    title='Error',
                )
                return

            theme_name, ok = QInputDialog.getText(
                self,
                'Save Theme',
                'Enter a name for the theme:',
            )
            if not ok:
                return

            sql.execute("""
                INSERT INTO themes (name, config)
                VALUES (?, ?)
            """, (theme_name, current_config_str))
            self.load()

        def delete_theme(self):
            theme_name = self.widgets[0].theme.currentText()
            if theme_name == 'Custom':
                return

            retval = display_messagebox(
                icon=QMessageBox.Warning,
                text=f"Are you sure you want to delete the theme '{theme_name}'?",
                title="Delete Theme",
                buttons=QMessageBox.Yes | QMessageBox.No,
            )

            if retval != QMessageBox.Yes:
                return

            sql.execute("""
                DELETE FROM themes
                WHERE name = ?
            """, (theme_name,))
            self.load()

        def get_current_display_config(self):
            display_page = self.widgets[1]
            roles_config_temp = sql.get_results("""
                SELECT name, config
                FROM roles
                """, return_type='dict'
            )
            roles_config = {role_name: json.loads(config) for role_name, config in roles_config_temp.items()}

            current_config = {
                'assistant': {
                    'bubble_bg_color': roles_config['assistant']['bubble_bg_color'],
                    'bubble_text_color': roles_config['assistant']['bubble_text_color'],
                },
                'code': {
                    'bubble_bg_color': roles_config['code']['bubble_bg_color'],
                    'bubble_text_color': roles_config['code']['bubble_text_color'],
                },
                'display': {
                    'primary_color': get_widget_value(display_page.primary_color),
                    'secondary_color': get_widget_value(display_page.secondary_color),
                    'text_color': get_widget_value(display_page.text_color),
                },
                'user': {
                    'bubble_bg_color': roles_config['user']['bubble_bg_color'],
                    'bubble_text_color': roles_config['user']['bubble_text_color'],
                },
            }
            return current_config

        class Page_Display_Themes(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.label_width = 185
                self.margin_left = 20
                self.propagate = False
                self.all_themes = {}
                self.schema = [
                    {
                        'text': 'Theme',
                        'type': ('Dark',),
                        'width': 100,
                        'default': 'Dark',
                    },
                ]

            def load(self):
                temp_themes = sql.get_results("""
                    SELECT name, config
                    FROM themes
                """, return_type='dict')
                self.all_themes = {theme_name: json.loads(config) for theme_name, config in temp_themes.items()}

                # load items into ComboBox
                with block_signals(self.theme):
                    self.theme.clear()
                    self.theme.addItems(['Custom'])
                    self.theme.addItems(self.all_themes.keys())

                current_display_config = self.parent.get_current_display_config()
                for theme_name in self.all_themes:
                    if self.all_themes[theme_name] == current_display_config:
                        # set self.theme (A ComboBox) to the current theme item, NOT setCurrentText
                        with block_signals(self.theme):
                            indx = self.theme.findText(theme_name)
                            self.theme.setCurrentIndex(indx)
                        return
                self.theme.setCurrentIndex(0)

            def after_init(self):
                self.theme.currentIndexChanged.connect(self.changeTheme)

            def changeTheme(self):
                theme_name = self.theme.currentText()
                if theme_name == 'Custom':
                    return

                patch_dicts = {
                    'settings': {
                        'display.primary_color': self.all_themes[theme_name]['display']['primary_color'],
                        'display.secondary_color': self.all_themes[theme_name]['display']['secondary_color'],
                        'display.text_color': self.all_themes[theme_name]['display']['text_color'],
                    },
                    'roles': {}
                }
                # patch settings table
                sql.execute("""
                    UPDATE `settings` SET `value` = json_patch(value, ?) WHERE `field` = 'app_config'
                """, (json.dumps(patch_dicts['settings']),))

                # todo all roles dynamically
                if 'user' in self.all_themes[theme_name]:
                    patch_dicts['roles']['user'] = {
                        'bubble_bg_color': self.all_themes[theme_name]['user']['bubble_bg_color'],
                        'bubble_text_color': self.all_themes[theme_name]['user']['bubble_text_color'],
                    }
                    # patch user role
                    sql.execute("""
                        UPDATE `roles` SET `config` = json_patch(config, ?) WHERE `name` = 'user'
                    """, (json.dumps(patch_dicts['roles']['user']),))
                if 'assistant' in self.all_themes[theme_name]:
                    patch_dicts['roles']['assistant'] = {
                        'bubble_bg_color': self.all_themes[theme_name]['assistant']['bubble_bg_color'],
                        'bubble_text_color': self.all_themes[theme_name]['assistant']['bubble_text_color'],
                    }
                    # patch assistant role
                    sql.execute("""
                        UPDATE `roles` SET `config` = json_patch(config, ?) WHERE `name` = 'assistant'
                    """, (json.dumps(patch_dicts['roles']['assistant']),))
                if 'code' in self.all_themes[theme_name]:
                    patch_dicts['roles']['code'] = {
                        'bubble_bg_color': self.all_themes[theme_name]['code']['bubble_bg_color'],
                        'bubble_text_color': self.all_themes[theme_name]['code']['bubble_text_color'],
                    }
                    # patch code role
                    sql.execute("""
                        UPDATE `roles` SET `config` = json_patch(config, ?) WHERE `name` = 'code'
                    """, (json.dumps(patch_dicts['roles']['code']),))

                page_settings = self.parent.parent
                system = page_settings.main.system
                system.config.load()
                system.roles.load()

                app_config = system.config.dict
                page_settings.load_config(app_config)
                page_settings.load()
                page_settings.main.apply_stylesheet()
                pass

        class Page_Display_Fields(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.parent = parent

                self.label_width = 185
                self.margin_left = 20
                self.conf_namespace = 'display'
                self.schema = [
                    {
                        'text': 'Primary color',
                        'type': 'ColorPickerWidget',
                        'default': '#ffffff',
                    },
                    {
                        'text': 'Secondary color',
                        'type': 'ColorPickerWidget',
                        'default': '#ffffff',
                    },
                    {
                        'text': 'Text color',
                        'type': 'ColorPickerWidget',
                        'default': '#ffffff',
                    },
                    {
                        'text': 'Text font',
                        'type': 'FontComboBox',
                        'default': 'Default',
                    },
                    {
                        'text': 'Text size',
                        'type': int,
                        'minimum': 6,
                        'maximum': 72,
                        'default': 12,
                    },
                    {
                        'text': 'Show bubble name',
                        'type': ('In Group', 'Always', 'Never',),
                        'default': 'In Group',
                    },
                    {
                        'text': 'Show bubble avatar',
                        'type': ('In Group', 'Always', 'Never',),
                        'default': 'In Group',
                    },
                    {
                        'text': 'Show waiting bar',
                        'type': ('In Group', 'Always', 'Never',),
                        'default': 'In Group',
                    },
                    {
                        'text': 'Bubble avatar position',
                        'type': ('Top', 'Middle',),
                        'default': 'Top',
                    },
                    {
                        'text': 'Bubble spacing',
                        'type': int,
                        'minimum': 0,
                        'maximum': 10,
                        'default': 5,
                    },
                    {
                        'text': 'Window margin',
                        'type': int,
                        'minimum': 0,
                        'maximum': 69,
                        'default': 6,
                    },
                    {
                        'text': 'Parameter line color',
                        'type': 'ColorPickerWidget',
                        'default': '#438BB9',
                    },
                    {
                        'text': 'Pinned pages',
                        'type': str,
                        'visible': False,
                        'default': '[]',
                    },
                    # {
                    #     'text': 'Pin blocks',
                    #     'type': bool,
                    #     'visible': False,
                    #     'default': True,
                    # },
                    # {
                    #     'text': 'Pin tools',
                    #     'type': bool,
                    #     'visible': False,
                    #     'default': True,
                    # },
                ]

            # def load(self):
            #     super().load()
            #     # self.parent.widgets[0].load()  # load theme
            #     # main = find_main_widget(self)

            def update_config(self):
                super().update_config()
                main = self.parent.parent.main
                main.system.config.load()
                main.apply_stylesheet()
                main.apply_margin()
                main.page_chat.message_collection.refresh_waiting_bar()
                self.load()  # reload theme combobox for custom
                self.parent.widgets[0].load()

    class Page_Role_Settings(ConfigDBTree):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                db_table='roles',
                query="""
                    SELECT
                        name,
                        id
                    FROM roles""",
                schema=[
                    {
                        'text': 'Roles',
                        'key': 'name',
                        'type': str,
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                ],
                add_item_prompt=('Add Role', 'Enter a name for the role:'),
                del_item_prompt=('Delete Role', 'Are you sure you want to delete this role?'),
                readonly=False,
                layout_type='horizontal',
                config_widget=self.Role_Config_Widget(parent=self),
                tree_header_hidden=True,
            )
            self.user_editable = True

        def on_edited(self):
            self.parent.main.system.roles.load()
            self.parent.main.apply_stylesheet()

        class Role_Config_Widget(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.label_width = 175
                self.schema = [
                    {
                        'text': 'Bubble bg color',
                        'type': 'ColorPickerWidget',
                        'default': '#3b3b3b',
                    },
                    {
                        'text': 'Bubble text color',
                        'type': 'ColorPickerWidget',
                        'default': '#c4c4c4',
                    },
                    {
                        'text': 'Bubble image size',
                        'type': int,
                        'minimum': 3,
                        'maximum': 100,
                        'default': 25,
                    },
                ]

    class Page_Files_Settings(ConfigTabs):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.IS_DEV_MODE = True
            self.main = find_main_widget(self)
            self.pages = {
                'Filesystem': self.Page_Filesystem(parent=self),
                'Extensions': self.Page_Extensions(parent=self),
                # 'Folders': self.Page_Folders(parent=self),
            }

        class Page_Filesystem(ConfigDBTree):
            def __init__(self, parent):
                super().__init__(
                    parent=parent,
                    db_table='files',
                    query="""
                        SELECT
                            name,
                            id,
                            folder_id
                        FROM files""",
                    schema=[
                        {
                            'text': 'Files',
                            'key': 'file',
                            'type': str,
                            'label_position': None,
                            'stretch': True,
                        },
                        {
                            'text': 'id',
                            'key': 'id',
                            'type': int,
                            'visible': False,
                        },
                    ],
                    add_item_prompt=('NA', 'NA'),
                    del_item_prompt=('NA', 'NA'),
                    tree_header_hidden=True,
                    readonly=True,
                    layout_type='horizontal',
                    config_widget=self.File_Config_Widget(parent=self),
                    folder_key='filesystem',
                    folders_groupable=True,
                )

            def add_item(self, column_vals=None, icon=None):
                with block_pin_mode():
                    file_dialog = QFileDialog()
                    file_dialog.setFileMode(QFileDialog.ExistingFile)
                    file_dialog.setOption(QFileDialog.ShowDirsOnly, False)
                    file_dialog.setFileMode(QFileDialog.Directory)
                    path, _ = file_dialog.getOpenFileName(None, "Choose Files", "", options=file_dialog.Options())

                if path:
                    self.add_path(path)

            def add_ext_folder(self):
                with block_pin_mode():
                    file_dialog = QFileDialog()
                    file_dialog.setFileMode(QFileDialog.Directory)
                    file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
                    path = file_dialog.getExistingDirectory(self, "Choose Directory", "")
                    if path:
                        self.add_path(path)

            def add_path(self, path):
                base_directory = os.path.dirname(path)
                directories = []
                while base_directory:
                    directories.append(os.path.basename(base_directory))
                    next_directory = os.path.dirname(base_directory)
                    base_directory = next_directory if next_directory != base_directory else None

                directories = reversed(directories)
                parent_id = None
                for directory in directories:
                    parent_id = super().add_folder(directory, parent_id)

                name = os.path.basename(path)
                config = json.dumps({'path': path, })
                sql.execute(f"INSERT INTO `files` (`name`, `folder_id`) VALUES (?, ?)", (name, parent_id,))
                last_insert_id = sql.get_scalar("SELECT seq FROM sqlite_sequence WHERE name=?", (self.db_table,))
                self.load(select_id=last_insert_id)
                return True

            def dragEnterEvent(self, event):
                # Check if the event contains file paths to accept it
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()

            def dragMoveEvent(self, event):
                # Check if the event contains file paths to accept it
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()

            def dropEvent(self, event):
                # Get the list of URLs from the event
                urls = event.mimeData().urls()

                # Extract local paths from the URLs
                paths = [url.toLocalFile() for url in urls]

                for path in paths:
                    self.add_path(path)

                event.acceptProposedAction()

            class File_Config_Widget(ConfigFields):
                def __init__(self, parent):
                    super().__init__(parent=parent)
                    self.label_width = 175
                    self.schema = []

        class Page_Extensions(ConfigDBTree):
            def __init__(self, parent):
                super().__init__(
                    parent=parent,
                    db_table='file_exts',
                    query="""
                        SELECT
                            name,
                            id,
                            folder_id
                        FROM file_exts
                        ORDER BY name""",
                    schema=[
                        {
                            'text': 'Name',
                            'key': 'name',
                            'type': str,
                            'stretch': True,
                        },
                        {
                            'text': 'id',
                            'key': 'id',
                            'type': int,
                            'visible': False,
                        },
                    ],
                    add_item_prompt=('Add extension', "Enter the file extension without the '.' prefix"),
                    del_item_prompt=('Delete extension', 'Are you sure you want to delete this extension?'),
                    readonly=False,
                    folder_key='file_exts',
                    layout_type='horizontal',
                    config_widget=self.Extensions_Config_Widget(parent=self),
                )

            def on_edited(self):
                self.parent.main.system.files.load()

            class Extensions_Config_Widget(ConfigFields):
                def __init__(self, parent):
                    super().__init__(parent=parent)
                    self.schema = [
                        {
                            'text': 'Default attachment method',
                            'type': ('Add path to message','Add contents to message','Encode base64',),
                            'default': 'Add path to message',
                            # 'width': 385,
                        },
                    ]

    class Page_VecDB_Settings(ConfigDBTree):
        def __init__(self, parent):
            self.IS_DEV_MODE = True
            super().__init__(
                parent=parent,
                db_table='vectordbs',
                query="""
                    SELECT
                        name,
                        id,
                        folder_id
                    FROM vectordbs""",
                schema=[
                    {
                        'text': 'Name',
                        'key': 'name',
                        'type': str,
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                ],
                add_item_prompt=('Add VecDB table', 'Enter a name for the table:'),
                del_item_prompt=('Delete VecDB table', 'Are you sure you want to delete this table?'),
                readonly=False,
                layout_type='horizontal',
                folder_key='vectordb_tables',
                config_widget=self.VectorDBConfig(parent=self),
            )

        def on_edited(self):
            self.parent.main.system.vectordbs.load()

        class VectorDBConfig(ConfigPlugin):
            def __init__(self, parent):
                super().__init__(
                    parent,
                    plugin_type='VectorDBSettings',
                    plugin_json_key='vec_db_provider',
                    plugin_label_text='VectorDB provider',
                    none_text='LanceDB'
                )
                self.default_class = self.LanceDB_VecDBConfig

            class LanceDB_VecDBConfig(ConfigTabs):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.pages = {
                        'Config': self.Page_VecDB_Config(parent=self),
                        # 'Test run': self.Page_Run(parent=self),
                    }

                class Page_VecDB_Config(ConfigJoined):
                    def __init__(self, parent):
                        super().__init__(parent=parent, layout_type='horizontal')
                        self.widgets = [
                            # self.Tool_Info_Widget(parent=self),
                            self.Env_Vars_Widget(parent=self),
                        ]

                    # class
                    class Env_Vars_Widget(ConfigJsonTree):
                        def __init__(self, parent):
                            super().__init__(parent=parent,
                                             add_item_prompt=('NA', 'NA'),
                                             del_item_prompt=('NA', 'NA'))
                            self.parent = parent
                            self.conf_namespace = 'env_vars'
                            self.schema = [
                                {
                                    'text': 'Variable',
                                    'type': str,
                                    'width': 120,
                                    'default': 'Variable name',
                                },
                                {
                                    'text': 'Value',
                                    'type': str,
                                    'stretch': True,
                                    'default': '',
                                },
                            ]

    class Page_Environments_Settings(ConfigDBTree):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                db_table='sandboxes',
                query="""
                    SELECT
                        name,
                        id,
                        folder_id
                    FROM sandboxes""",
                schema=[
                    {
                        'text': 'Name',
                        'key': 'name',
                        'type': str,
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                ],
                add_item_prompt=('Add Environment', 'Enter a name for the environment:'),
                del_item_prompt=('Delete Environment', 'Are you sure you want to delete this environment?'),
                readonly=False,
                layout_type='horizontal',
                folder_key='sandboxes',
                config_widget=self.EnvironmentConfig(parent=self),
            )

        def on_edited(self):
            self.parent.main.system.environments.load()

        class EnvironmentConfig(ConfigJoined):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.widgets = [
                    self.EnvironmentPlugin(parent=self),
                ]

            class EnvironmentPlugin(ConfigPlugin):
                def __init__(self, parent):
                    super().__init__(
                        parent,
                        plugin_type='EnvironmentSettings',
                        plugin_json_key='sandbox_type',  # todo - rename
                        plugin_label_text='Environment Type',
                        none_text='Local',
                        default_class=EnvironmentSettings,
                    )

    class Page_Logs_Settings(ConfigDBTree):
        def __init__(self, parent):
            super().__init__(
                parent=parent,
                db_table='logs',
                query="""
                    SELECT
                        name,
                        id,
                        folder_id
                    FROM logs""",
                schema=[
                    {
                        'text': 'Name',
                        'key': 'name',
                        'type': str,
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                ],
                add_item_prompt=None,
                del_item_prompt=('Delete Log', 'Are you sure you want to delete this log?'),
                readonly=True,
                layout_type='vertical',
                folder_key='logs',
                config_widget=self.LogConfig(parent=self),
            )

        def on_edited(self):
            self.parent.main.system.logs.load()

        class LogConfig(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.schema = [
                    {
                        'text': 'Log type',
                        'type': ('File', 'Database', 'API',),
                        'default': 'File',
                    },
                    {
                        'text': 'Log path',
                        'type': str,
                        'default': '',
                    },
                    {
                        'text': 'Log level',
                        'type': ('Debug', 'Info', 'Warning', 'Error', 'Critical',),
                        'default': 'Info',
                    },
                    {
                        'text': 'Log format',
                        'type': str,
                        'default': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    },
                ]

    class Page_Workspace_Settings(ConfigDBTree):
        def __init__(self, parent):
            self.IS_DEV_MODE = True
            super().__init__(
                parent=parent,
                db_table='workspaces',
                query="""
                    SELECT
                        name,
                        id,
                        folder_id
                    FROM workspaces""",
                schema=[
                    {
                        'text': 'Workspaces',
                        'key': 'name',
                        'type': str,
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                ],
                add_item_prompt=('Add Workspace', 'Enter a name for the workspace:'),
                del_item_prompt=('Delete Workspace', 'Are you sure you want to delete this workspace?'),
                readonly=False,
                layout_type='horizontal',
                folder_key='workspaces',
                config_widget=self.WorkspaceConfig(parent=self),
            )

        def on_edited(self):
            self.parent.main.system.workspaces.load()

        class WorkspaceConfig(ConfigFields):
            def __init__(self, parent):
                super().__init__(parent=parent)
                self.schema = [
                    {
                        'text': 'Environment',
                        'type': 'EnvironmentComboBox',
                        'default': 'Local',
                    },
                ]

    class Page_Plugin_Settings(ConfigTabs):
        def __init__(self, parent):
            super().__init__(parent=parent)
            self.conf_namespace = 'plugins'

            self.pages = {
                # 'GPT Pilot': self.Page_Test(parent=self),
                # 'CrewAI': Page_Settings_CrewAI(parent=self),
                # 'Matrix': Page_Settings_Matrix(parent=self),
                'OAI': Page_Settings_OAI(parent=self),
                # 'Test Pypi': self.Page_Pypi_Packages(parent=self),
            }

    class Page_Sets_Settings(ConfigDBTree):
        def __init__(self, parent):
            self.IS_DEV_MODE = True
            super().__init__(
                parent=self,
                db_table='contexts',
                query="""
                    SELECT
                        c.name,
                        c.id,
                        CASE
                            WHEN json_extract(c.config, '$.members') IS NOT NULL THEN
                                CASE
                                    WHEN json_array_length(json_extract(c.config, '$.members')) > 2 THEN
                                        json_array_length(json_extract(c.config, '$.members')) || ' members'
                                    WHEN json_array_length(json_extract(c.config, '$.members')) = 2 THEN
                                        COALESCE(json_extract(json_extract(c.config, '$.members'), '$[1].config."info.name"'), 'Assistant')
                                    WHEN json_extract(json_extract(c.config, '$.members'), '$[1].config._TYPE') = 'agent' THEN
                                        json_extract(json_extract(c.config, '$.members'), '$[1].config."info.name"')
                                    ELSE
                                        json_array_length(json_extract(c.config, '$.members')) || ' members'
                                END
                            ELSE
                                CASE
                                    WHEN json_extract(c.config, '$._TYPE') = 'workflow' THEN
                                        '1 member'
                                    ELSE
                                        COALESCE(json_extract(c.config, '$."info.name"'), 'Assistant')
                                END
                        END as member_count,
                        CASE
                            WHEN json_extract(config, '$._TYPE') = 'workflow' THEN
                                (
                                    SELECT GROUP_CONCAT(json_extract(m.value, '$.config."info.avatar_path"'), '//##//##//')
                                    FROM json_each(json_extract(config, '$.members')) m
                                    WHERE COALESCE(json_extract(m.value, '$.del'), 0) = 0
                                )
                            ELSE
                                COALESCE(json_extract(config, '$."info.avatar_path"'), '')
                        END AS avatar,
                        c.folder_id
                    FROM contexts c
                    LEFT JOIN (
                        SELECT
                            context_id,
                            MAX(id) as latest_message_id
                        FROM contexts_messages
                        GROUP BY context_id
                    ) cmsg ON c.id = cmsg.context_id
                    WHERE c.parent_id IS NULL
                    AND c.kind = 'SET'
                    GROUP BY c.id
                    ORDER BY
                        COALESCE(cmsg.latest_message_id, 0) DESC
                    LIMIT ? OFFSET ?;
                    """,
                schema=[
                    {
                        'text': 'name',
                        'type': str,
                        'image_key': 'avatar',
                        'stretch': True,
                    },
                    {
                        'text': 'id',
                        'key': 'id',
                        'type': int,
                        'visible': False,
                    },
                    {
                        'key': 'member_count',
                        'text': '',
                        'type': str,
                        'width': 100,
                    },
                    {
                        'key': 'avatar',
                        'text': '',
                        'type': str,
                        'visible': False,
                    },
                ],
                kind='SET',
                dynamic_load=True,
                add_item_prompt=('Add Context', 'Enter a name for the context:'),
                del_item_prompt=('Delete Context', 'Are you sure you want to permanently delete this context?'),
                layout_type='vertical',
                config_widget=None,
                tree_header_hidden=True,
                folder_key='sets',
                init_select=False,
                filterable=True,
                searchable=True,
                archiveable=True,
            )

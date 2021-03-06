# coding:utf8


import os
import imp
import time
import types
import random
import traceback

from .. import utils


def default_plugin__accept_request(self, msg, rsp, utils, *args, **kwargs):
    if msg.was_appeal and msg.args[0].lower() in self.keywords:
        return True

    return False


class Pluginmanager(object):
    def __init__(self, bot, vkr):
        self.plugins = {}
        self.plugin_list = []
        self.builtin_plugin_list = []
        self.custom_plugin_list = []
        self.log = lambda *x, **y: None
        self.bot = bot
        self.utils = PluginUtils(self, self.bot, vkr, self.log)

    def plugin_respond(self, msg, rsp):
        for name in self.plugin_list:
            if not self.plugins[name]._accept_request(msg, rsp, self.utils):
                continue

            user_access_level = self.utils.get_user_access_level(msg)

            if user_access_level < self.plugins[name].protection:
                rsp.text = (
                    u'Для использования команды необходим уровень доступа %d.\n'
                    u'Ваш уровень доступа: %d'
                        % (self.plugins[name].protection, user_access_level)
                )
                break

            if self.plugins[name].argument_required:
                if len(msg.args) < 2:
                    rsp.text = \
                        u'Эту команду можно использовать только с аргументом'
                    break

            rsp = self.plugins[name].respond(msg, rsp, self.utils)
            break

        return rsp

    def load_plugins(self):
        self.plugins = {}
        self.plugin_list = []
        self.builtin_plugin_list = []
        self.custom_plugin_list = []

        if not os.path.exists(utils.CUSTOM_PLUGIN_DIR):
            self.log(
                u'Создание директории для пользовательских плагинов: %s ...'
                    % utils.CUSTOM_PLUGIN_DIR, 1
            )
            os.mkdir(utils.CUSTOM_PLUGIN_DIR)

        self.log(u'Чтение встроенных плагинов ...', 0)
        self._load_plugins_from(utils.PLUGIN_DIR)

        for p in self.plugins:
            self.builtin_plugin_list.append(p)

        self.log(u'Чтение пользовательских плагинов ...', 1)
        self._load_plugins_from(utils.CUSTOM_PLUGIN_DIR)

        for p in sorted(self.plugins, key=lambda x: self.plugins[x].priority,
                        reverse=True):
            self.plugin_list.append(p)

        self.builtin_plugin_list = set(self.builtin_plugin_list)

        self.custom_plugin_list = \
            set(set(self.plugin_list) - self.builtin_plugin_list)

        self.log(
            u'Загружены плагины: [b]%s[/b]' % ', '.join(self.plugin_list), 0)

    def _load_plugins_from(self, path):
        files = sorted(os.listdir(path))  # sorting to ensure that .py goes first
        included = []

        for f in files:
            if f.startswith('plugin_'):
                try:
                    if f.endswith('.py'):
                        if f + 'c' in files:
                            if os.path.getmtime(os.path.join(path, f + 'c')) > os.path.getmtime(os.path.join(path, f)):
                                # .pyc newer
                                continue

                        elif f + 'o' in files:
                            if os.path.getmtime(os.path.join(path, f + 'o')) > os.path.getmtime(os.path.join(path, f)):
                                # .pyo newer
                                continue

                        self._add_plugin(
                            imp.load_source('', os.path.join(path, f)), f, f[7:-3])

                        included.append(f)

                    elif f.endswith('.pyc') or f.endswith('.pyo'):
                        if f[:-1] in included:
                            continue

                        if f.endswith('c') and f[:-1] + 'o' in files:
                            if os.path.getmtime(os.path.join(path, f[:-1] + 'o')) > os.path.getmtime(os.path.join(path, f)):
                                # .pyo newer
                                continue
                        elif f[:-1] + 'c' in files:
                            if os.path.getmtime(os.path.join(path, f[:-1] + 'c')) > os.path.getmtime(os.path.join(path, f)):
                                # .pyc newer
                                continue

                        self._add_plugin(
                            imp.load_compiled('', os.path.join(path, f)), f, f[7:-4])

                        included.append(f[:-1])

                except Exception:
                    self.log(u'[b]Ошибка при загрузке плагина %s[/b]' % f, 2)
                    self.log(traceback.format_exc().decode('utf8'), 2)

    def _add_plugin(self, plugin, f, name):
        p = plugin.Plugin()

        if getattr(p, 'disabled', False):
            return

        if getattr(p, 'name', None) is None:
            self.log(
                u'[b]Предупреждение: отсутствует имя модуля %s. Использую %s[/b]' 
                    % (f, name), 1
            )
            p.name = name

        if len(getattr(p, 'keywords', ())) == 0:
            self.log(u'[b]Ошибка: Нет ключевых слов для модуля %s[/b]' % f, 1)
            return
        
        if getattr(p, '__doc__', None) is None:
            self.log(
                u'[b]Предупреждение: модуль %s не имеет документации[/b]' % f, 1
            )
            p.__doc__ = ''

        if not hasattr(p, 'protection'):
            self.log(
                u'[b]Предупреждение: модуль %s не имеет информации о защите. '
                u'Использую 0[/b]' % f, 1
            )
            p.protection = 0

        if not hasattr(p, 'argument_required'):
            self.log(
                u'[b]Предупреждение: модуль %s не имеет информации о '
                u'необходимости аргумента. Использую False[/b]' % f, 1
            )
            p.argument_required = False

        if not hasattr(p, 'priority'):
            p.priority = 0

        if not hasattr(p, '_accept_request'):
            p._accept_request = \
                types.MethodType(default_plugin__accept_request, p)

        if p.name in self.plugins:
            self.log(
                u'Предупреждение: модуль [b]%s[/b] будет переназначен ...' %
                p.name, 1)

            if p.name in self.builtin_plugin_list:
                self.builtin_plugin_list.remove(p.name)

            if p.name in self.custom_plugin_list:
                self.custom_plugin_list.remove(p.name)

        self.plugins[name] = p

    def set_logging_function(self, logging_function):
        self.log = logging_function
        self.utils.log = logging_function
        self.log(u'Подключена функция логгирования для менеджера плагинов', 0)


class PluginUtils(object):
    """This class contains all nesessary utils for plugins
    """

    def __init__(self, pm, bot, vkr, log):
        self.__pm = pm
        self.__bot = bot
        self.vkr = vkr
        self.log = log

    def get_settings(self):
        return self.__bot.settings

    def get_blacklist(self):
        return self.__bot.blacklist

    def get_whitelist(self):
        return self.__bot.whitelist

    def get_custom_commands(self):
        return self.__bot.custom_commands

    def get_settings(self, keys, section='Plugins'):
        return utils.get_settings(keys, section=section)

    def save_setting(self, key, val, section='Plugins'):
        self.log(u'Обновляю настройки: %s=%s' % (key, val), 0)
        utils.save_setting(key, val, section=section)

        if key in self.__bot.settings:
            self.__bot.settings[key] = val

        self.__bot.is_settings_changed = True

    def save_blacklist(self, blacklist):
        utils.save_blacklist(blacklist)
        self.__bot.blacklist = blacklist

    def save_whitelist(self, whitelist):
        utils.save_whitelist(whitelist)
        self.__bot.whitelist = whitelist

    def save_custom_commands(self, custom_commands):
        utils.save_custom_commands(custom_commands)
        self.__bot.custom_commands = custom_commands

    def clear_message_queue(self):
        self.__bot.mlpd = None

    def get_user_access_level(self, msg):
        whitelist = self.get_whitelist()

        if msg.out:
            user_access_level = 4
        elif msg.real_user_id in whitelist:
            user_access_level = whitelist[msg.real_user_id]
        else:
            user_access_level = 0

        return user_access_level

    def safe_format(self, *args, **kwargs):
        return utils.safe_format(*args, **kwargs)

    def get_plugin_list(self):
        return self.__pm.plugin_list

    def get_builtin_plugin_list(self):
        return self.__pm.builtin_plugin_list

    def get_custom_plugin_list(self):
        return self.__pm.custom_plugin_list

    def get_plugin(self, name):
        return self.__pm.plugins[name] if name in self.__pm.plugin_list else None

    def stop_bot(self):
        self.log(u'Вызов функции остановки', 0)
        self.__bot.runtime_error = 0

    def set_startup_response(self, response):
        self.__bot.startup_response = response

    def restart_bot(self):
        self.log(u'Вызов функции перезагрузки', 0)
        self.__bot.runtime_error = 1
# -*- coding: utf-8 -*-
# Copyright 2007-2016 The HyperSpyUI developers
#
# This file is part of HyperSpyUI.
#
# HyperSpyUI is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# HyperSpyUI is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with HyperSpyUI.  If not, see <http://www.gnu.org/licenses/>.
"""
Created on Mon Oct 27 21:17:42 2014

@author: Vidar Tonaas Fauske
"""

# Set proper backend for matplotlib
import matplotlib
matplotlib.use('module://hyperspyui.mdi_mpl_backend')
matplotlib.interactive(True)

import os
import warnings
import sys

from python_qt_binding import QtGui, QtCore
from QtCore import *
from QtGui import *

from widgets.consolewidget import ConsoleWidget
import hyperspyui.mdi_mpl_backend
from pluginmanager import PluginManager
from hyperspyui.settings import Settings
from hyperspyui.widgets.settingsdialog import SettingsDialog
from hyperspyui.smartcolorsvgiconengine import SmartColorSVGIconEngine


def tr(text):
    return QCoreApplication.translate("MainWindow", text)


def lowpriority():
    """ Set the priority of the process to below-normal."""

    if sys.platform == 'win32':
        # Based on:
        #   "Recipe 496767: Set Process Priority In Windows" on ActiveState
        #   http://code.activestate.com/recipes/496767/
        try:
            import win32api
            import win32process
            import win32con
        except ImportError as e:
            warnings.warn("Could not set process priority: %s" % e.message)
            return

        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(
            handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
    else:
        import os

        os.nice(1)


def normalpriority():
    """ Set the priority of the process to below-normal."""

    if sys.platform == 'win32':
        # Based on:
        #   "Recipe 496767: Set Process Priority In Windows" on ActiveState
        #   http://code.activestate.com/recipes/496767/
        try:
            import win32api
            import win32process
            import win32con
        except ImportError as e:
            warnings.warn("Could not set process priority: %s" % e.message)
            return

        pid = win32api.GetCurrentProcessId()
        handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
        win32process.SetPriorityClass(
            handle, win32process.NORMAL_PRIORITY_CLASS)
    else:
        import os

        # Reset nice to 0
        os.nice(-os.nice(0))


class MainWindowLayer1(QMainWindow):

    """
    Base layer in application stack. Should handle the connection to our custom
    matplotlib backend, and manage the Figures. As such, it does not know
    anything about hyperspy, and can readily be reused for other projects.
    Should also set up basic UI with utilities, and relevant functions for
    inhereting classes to override.
    """

    def __init__(self, parent=None):
        super(MainWindowLayer1, self).__init__(parent)

        # Setup settings:
        self.settings = Settings(self, 'General')
        # Default setting values:
        self.settings.set_default('toolbar_button_size', 32)
        self.settings.set_default('default_widget_floating', False)
        self.settings.set_default('working_directory', "")
        self.settings.set_default('low_process_priority', False)
        # Override any possible invalid stored values, which could prevent load
        if 'toolbar_button_size' not in self.settings or \
                not isinstance(self.settings['toolbar_button_size'], int):
            self.settings['toolbar_button_size'] = 32
        if self.low_process_priority:
            lowpriority()

        # State varaibles
        self.should_capture_traits = None
        self.active_tool = None

        # Collections
        self.widgets = []   # Widgets in widget bar
        self.figures = []   # Matplotlib figures
        self.editors = []   # EditorWidgets
        self.traits_dialogs = []
        self.actions = {}
        self._action_selection_cbs = {}
        self.toolbars = {}
        self.menus = {}
        self.tools = []
        self.plugin_manager = None

        # MPL backend bindings
        hyperspyui.mdi_mpl_backend.connect_on_new_figure(self.on_new_figure)
        hyperspyui.mdi_mpl_backend.connect_on_destroy(self.on_destroy_figure)

        # Create UI
        self.windowmenu = None
        self.create_ui()

        # Connect figure management functions
        self.main_frame.subWindowActivated.connect(self.on_subwin_activated)

        # Save standard layout/state
        self.settings.set_default('_geometry', self.saveGeometry())
        self.settings.set_default('_windowState', self.saveState())

        # Restore layout/state if saved
        geometry = self.settings['_geometry']
        state = self.settings['_windowState']
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)

    @property
    def toolbar_button_size(self):
        return self.settings['toolbar_button_size', int]

    @toolbar_button_size.setter
    def toolbar_button_size(self, value):
        self.settings['toolbar_button_size'] = value
        self.setIconSize(
            QSize(self.toolbar_button_size, self.toolbar_button_size))

    @property
    def cur_dir(self):
        return self.settings['working_directory']

    @cur_dir.setter
    def cur_dir(self, value):
        self.settings['working_directory'] = value

    @property
    def low_process_priority(self):
        return self.settings['low_process_priority', bool]

    @low_process_priority.setter
    def low_process_priority(self, value):
        self.settings['low_process_priority'] = value
        if value:
            lowpriority()
        else:
            normalpriority()

    @property
    def plugins(self):
        return self.plugin_manager.plugins

    def handleSecondInstance(self, argv):
        # overload if needed
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized |
                            QtCore.Qt.WindowActive)
        self.activateWindow()

    def closeEvent(self, event):
        self.settings['_geometry'] = self.saveGeometry()
        self.settings['_windowState'] = self.saveState()
        return super(MainWindowLayer1, self).closeEvent(event)

    def reset_geometry(self):
        self.settings.restore_key_default('_geometry')
        self.settings.restore_key_default('_windowState')
        geometry = self.settings['_geometry']
        state = self.settings['_windowState']
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
        self.setWindowState(Qt.WindowMaximized)

    def create_ui(self):
        self.setIconSize(
            QSize(self.toolbar_button_size, self.toolbar_button_size))
        self.main_frame = QMdiArea()

        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)

        self.init_plugins()

        self.create_default_actions()   # Goes before menu/toolbar/widgetbar

        # Needs to go before menu, so console can be in menu
        self.create_console()
        # This needs to happen before the widgetbar and toolbar
        self.create_menu()
        self.create_toolbars()
        self.create_widgetbar()

        self.setCentralWidget(self.main_frame)

    def init_plugins(self):
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.init_plugins()

    def create_default_actions(self):
        """
        Create default actions that can be used for e.g. toolbars and menus,
        or triggered manually.
        """
        self.plugin_manager.create_actions()

        self.selectable_tools = QActionGroup(self)
        self.selectable_tools.setExclusive(True)

        # Tile windows action
        ac_tile = QAction(tr("Tile"), self)
        ac_tile.setStatusTip(tr("Arranges all figures in a tile pattern"))
        self.connect(ac_tile, SIGNAL('triggered()'),
                     self.main_frame.tileSubWindows)
        self.actions['tile_windows'] = ac_tile

        # Cascade windows action
        ac_cascade = QAction(tr("Cascade"), self)
        ac_cascade.setStatusTip(
            tr("Arranges all figures in a cascade pattern"))
        self.connect(ac_cascade, SIGNAL('triggered()'),
                     self.main_frame.cascadeSubWindows)
        self.actions['cascade_windows'] = ac_cascade

        # Close all figures action
        ac_close_figs = QAction(tr("Close all"), self)
        ac_close_figs.setStatusTip(tr("Closes all matplotlib figures"))
        self.connect(ac_close_figs, SIGNAL('triggered()'),
                     lambda: matplotlib.pyplot.close("all"))
        self.actions['close_all_windows'] = ac_close_figs

        # Reset geometry action
        ac_reset_layout = QAction(tr("Reset layout"), self)
        ac_reset_layout.setStatusTip(tr("Resets layout of toolbars and "
                                        "widgets"))
        self.connect(ac_reset_layout, SIGNAL('triggered()'),
                     self.reset_geometry)
        self.actions['reset_layout'] = ac_reset_layout

    def create_menu(self):
        mb = self.menuBar()
        # Window menu is filled in add_widget and add_figure
        self.windowmenu = mb.addMenu(tr("&Windows"))
        self.windowmenu.addAction(self._console_dock.toggleViewAction())
        # Figure windows go below this separator. Other windows can be added
        # above it with insertAction(self.windowmenu_sep, QAction)
        self.windowmenu_sep = self.windowmenu.addSeparator()
        self.windowmenu.addAction(self.actions['tile_windows'])
        self.windowmenu.addAction(self.actions['cascade_windows'])
        self.windowmenu.addSeparator()
        self.windowmenu.addAction(self.actions['close_all_windows'])
        self.windowmenu_actions_sep = self.windowmenu.addSeparator()

        self.plugin_manager.create_menu()

    def create_tools(self):
        """Override to create tools on UI construction.
        """
        self.plugin_manager.create_tools()

    def create_toolbars(self):
        """
        Override to create toolbars and toolbar buttons on UI construction.
        It is called after create_default_action(), so add_toolbar_button()
        can be used to add previously defined acctions.
        """
        self.create_tools()
        self.plugin_manager.create_toolbars()

    def create_widgetbar(self):
        """
        The widget bar itself is created and managed implicitly by Qt. Override
        this function to add widgets on UI construction.
        """

        self.plugin_manager.create_widgets()

    def edit_settings(self):
        """
        Shows a dialog for editing the application and plugins settings.
        """
        d = SettingsDialog(self, self)
        d.settings_changed.connect(self.on_settings_changed)
        d.exec_()

    def on_settings_changed(self):
        """
        Callback for SettingsDialog, or anything else that updates settings
        and need to apply the change.
        """
        # Due to the way the property is defined, this updates the UI:
        self.toolbar_button_size = self.toolbar_button_size
        self.low_process_priority = self.low_process_priority

    def select_tool(self, tool):
        if self.active_tool is not None:
            try:
                self.active_tool.disconnect_windows(self.figures)
            except Exception as e:
                warnings.warn("Exception disabling tool %s: %s" % (
                    self.active_tool.get_name(), e.message))
        self.active_tool = tool
        tool.connect_windows(self.figures)

    # --------- Figure management ---------

    # --------- MPL Events ---------

    def on_new_figure(self, figure, userdata=None):
        """
        Callback for MPL backend.
        """
        self.main_frame.addSubWindow(figure)
        self.figures.append(figure)
        self.windowmenu.addAction(figure.activateAction())
        for tool in self.tools:
            if tool.single_action() is not None:
                tool.connect_windows(figure)
        if self.active_tool is not None:
            self.active_tool.connect_windows(figure)

    def on_destroy_figure(self, figure, userdata=None):
        """
        Callback for MPL backend.
        """
        if figure in self.figures:
            self.figures.remove(figure)
        self.windowmenu.removeAction(figure.activateAction())
        for tool in self.tools:
            if tool.single_action() is not None:
                tool.disconnect_windows(figure)
        if self.active_tool is not None:
            self.active_tool.disconnect_windows(figure)
        self.main_frame.removeSubWindow(figure)

    # --------- End MPL Events ---------

    def on_subwin_activated(self, mdi_figure):
        if mdi_figure and os.environ['QT_API'] == 'pyside':
            mdi_figure.activateAction().setChecked(True)
        self.check_action_selections(mdi_figure)

    def check_action_selections(self, mdi_figure=None):
        if mdi_figure is None:
            mdi_figure = self.main_frame.activeSubWindow()
        for key, cb in self._action_selection_cbs.iteritems():
            cb(mdi_figure, self.actions[key])

    # --------- End figure management ---------

    # --------- UI utility finctions ---------

    def make_icon(self, icon):
        if not isinstance(icon, QIcon):
            if isinstance(icon, basestring) and not os.path.isfile(icon):
                sugg = os.path.dirname(__file__) + '/images/' + icon
                if os.path.isfile(sugg):
                    icon = sugg
            if isinstance(icon, basestring) and (
                    icon.endswith('svg') or
                    icon.endswith('svgz') or
                    icon.endswith('svg.gz')):
                ie = SmartColorSVGIconEngine()
                path = icon
                icon = QIcon(ie)
                icon.addFile(path)
            else:
                icon = QIcon(icon)
        else:
            icon = QIcon(SmartColorSVGIconEngine(icon))
        return icon

    def get_figure_filepath_suggestion(self, figure, deault_ext=None):
        canvas = figure.widget()
        if deault_ext is None:
            deault_ext = canvas.get_default_filetype()

        f = canvas.get_default_filename()
        if not f:
            f = self.cur_dir

        # Analyze suggested filename
        base, tail = os.path.split(f)
        fn, ext = os.path.splitext(tail)

        # If no directory in filename, use self.cur_dir's dirname
        if base is None or base == "":
            base = os.path.dirname(self.cur_dir)
        # If extension is not valid, use the defualt
        if ext not in canvas.get_supported_filetypes():
            ext = deault_ext

        # Build suggestion and return
        path_suggestion = os.path.sep.join((base, fn))
        path_suggestion = os.path.extsep.join((path_suggestion, ext))
        return path_suggestion

    def save_figure(self, figure=None):
        if figure is None:
            figure = self.main_frame.activeSubWindow()
            if figure is None:
                return
        path_suggestion = self.get_figure_filepath_suggestion(figure)
        canvas = figure.widget()

        # Build type selection string
        def_type = os.path.extsep + canvas.get_default_filetype()
        extensions = canvas.get_supported_filetypes_grouped()
        type_choices = u"All types (*.*)"
        for group, exts in extensions.iteritems():
            fmt = group + \
                ' (' + \
                '; '.join([os.path.extsep + sube for sube in exts]) + ')'
            type_choices = ';;'.join((type_choices, fmt))
            if def_type[1:] in exts:
                def_type = fmt

        # Present filename prompt
        filename = QFileDialog.getSaveFileName(self, tr("Save file"),
                                               path_suggestion, type_choices,
                                               def_type)[0]
        if filename:
            canvas.figure.savefig(filename)

    # --------- Console functions ---------

    def _get_console_exec(self):
        return ""

    def _get_console_exports(self):
        return {'ui': self}

    def _get_console_config(self):
        return None

    def on_console_executing(self, source):
        """
        Override when inherited to perform actions before exectuing 'source'.
        """
        pass

    def on_console_executed(self, response):
        """
        Override when inherited to perform actions after executing, given the
        'response' returned.
        """
        pass

    def create_console(self):
        # We could inherit QAction, and have it reroute when it triggers,
        # and then drop route when it finishes, however this will not catch
        # interactive dialogs and such.
        c = self._get_console_config()
        control = ConsoleWidget(config=c)
        control.executing.connect(self.on_console_executing)
        control.executed.connect(self.on_console_executed)

        # This is where we push variables to the console
        ex = self._get_console_exec()
        push = self._get_console_exports()
        control.ex(ex)
        control.push(push)

        self.console = control

        self._console_dock = QDockWidget()
        self._console_dock.setObjectName('console_widget')
        self._console_dock.setWidget(control)
        self._console_dock.setWindowTitle("Console")
        self.addDockWidget(Qt.BottomDockWidgetArea, self._console_dock)

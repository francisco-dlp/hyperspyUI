# -*- coding: utf-8 -*-
"""
Created on Sun Mar 01 15:18:30 2015

@author: Vidar Tonaas Fauske
"""

from hyperspyui.plugins.plugin import Plugin

from python_qt_binding import QtGui, QtCore
from QtCore import *
from QtGui import *

import hyperspy.utils.plot


def tr(text):
    return QCoreApplication.translate("MirrorPlotPlugin", text)


class MirrorPlotPlugin(Plugin):
    name = "Mirror plot"

    def create_actions(self):
        self.add_action('mirror', "Mirror navigation", self.mirror_navi,
                        icon='mirror.svg',
                        selection_callback=self.ui.select_signal,
                        tip="Mirror navigation axes of selected signals")
        self.add_action('share_nav', "Share navigation", self.share_navi,
                        icon='intersection.svg',
                        selection_callback=self.ui.select_signal,
                        tip="Mirror navigation axes of selected signals")

    def create_menu(self):
        self.add_menuitem('Signal', self.ui.actions['mirror'])
        self.add_menuitem('Signal', self.ui.actions['share_nav'])

    def create_toolbars(self):
        self.add_toolbar_button("Signal", self.ui.actions['mirror'])
        self.add_toolbar_button("Signal", self.ui.actions['share_nav'])

    def share_navi(self, uisignals=None):
        self.mirror_navi(uisignals, shared_nav=True)

    def mirror_navi(self, uisignals=None, shared_nav=False):
        # Select signals
        if uisignals is None:
            uisignals = self.ui.get_selected_wrappers()
        if len(uisignals) < 2:
            mb = QMessageBox(QMessageBox.Information, tr("Select two or more"),
                             tr("You need to select two or more signals" +
                                " to mirror"), QMessageBox.Ok)
            mb.exec_()
            return

        signals = [s.signal for s in uisignals]

        # hyperspy closes, and then recreates figures when mirroring
        # the navigators. To keep UI from flickering, we suspend updates.
        # SignalWrapper also saves and then restores window geometry
        self.ui.setUpdatesEnabled(False)
        try:
            if shared_nav:
                navs = ["auto"]
                navs.extend([None] * (len(signals)-1))
                hyperspy.utils.plot.plot_signals(signals, sync=True,
                                                 navigator_list=navs)
            else:
                hyperspy.utils.plot.plot_signals(signals, sync=True)
        finally:
            self.ui.setUpdatesEnabled(True)    # Continue updating UI

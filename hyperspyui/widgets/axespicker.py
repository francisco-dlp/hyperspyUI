# -*- coding: utf-8 -*-
# Copyright 2014-2016 The HyperSpyUI developers
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


from python_qt_binding import QtGui, QtCore

from hyperspyui.widgets.extendedqwidgets import ExToolWindow


class AxesPickerDialog(ExToolWindow):
    def __init__(self, ui, signal):
        super().__init__(ui)
        self.ui = ui
        self.signal = signal
        self.create_controls()
        self.setWindowTitle("Select axes")

    @property
    def selected_axes(self):
        sel = self.list.selectedItems()
        return [i.data(QtCore.Qt.UserRole) for i in sel]

    def create_controls(self):
        self.list = QtGui.QListWidget()
        for ax in self.signal.axes_manager._get_axes_in_natural_order():
            rep = '%s axis, size: %i' % (ax._get_name(), ax.size)
            item = QtGui.QListWidgetItem(rep, self.list)
            item.setData(QtCore.Qt.UserRole, ax)
            self.list.addItem(item)
        self.list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        btns = QtGui.QDialogButtonBox(
            QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel,
            QtCore.Qt.Horizontal)

        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        vbox = QtGui.QVBoxLayout(self)
        vbox.addWidget(self.list)
        vbox.addWidget(btns)

        self.setLayout(vbox)

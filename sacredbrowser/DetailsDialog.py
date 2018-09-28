from . import BrowserState

from PyQt5 import QtCore, QtGui, QtWidgets

import re
import os

FilenameRole = QtCore.Qt.UserRole + 1


# This is the dialog which displays details about a single experiment instance.
class DetailsDialog(QtWidgets.QDialog):

    def __init__(self,app,experiment,filesystem):
        super(DetailsDialog,self).__init__()
        self._app = app
        self._experiment = experiment
        self._filesystem = filesystem

        self._make_layout()

        self._make_config_model()
        self._make_entry_model()
        self._make_files_model()

        # connections
        self._ok_button.clicked.connect(self.accept)
        self._preview_file_button.clicked.connect(self._slot_preview_button_clicked)
        self._save_file_button.clicked.connect(self._slot_save_button_clicked)

        self._update_preview_buttons()

    def _make_layout(self):
        # widgets 
        self._config_label = QtWidgets.QLabel('Configuration')
        self._config_list = QtWidgets.QListView()
        self._config_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._config_display = QtWidgets.QTextEdit()
        self._config_display.setReadOnly(True)
        
        self._entry_label = QtWidgets.QLabel('Database Entry')
        self._entry_list = QtWidgets.QListView()
        self._entry_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._entry_display = QtWidgets.QTextEdit()
        self._entry_display.setReadOnly(True)

        self._files_label = QtWidgets.QLabel('Attached Files')
        self._files_list = QtWidgets.QListView()
        self._files_list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._preview_file_button = QtWidgets.QPushButton('&Preview')
        self._save_file_button = QtWidgets.QPushButton('&Save')

        self._ok_button = QtWidgets.QPushButton('&OK')
                
        self._main_layout = QtWidgets.QGridLayout()

        self._main_layout.addWidget(self._config_label,0,0,1,2)
        self._main_layout.addWidget(self._config_list,1,0)
        self._main_layout.addWidget(self._config_display,1,1)

        self._main_layout.addWidget(self._entry_label,2,0,1,2)
        self._main_layout.addWidget(self._entry_list,3,0)
        self._main_layout.addWidget(self._entry_display,3,1)

        self._main_layout.addWidget(self._files_label,4,0,1,2)
        self._main_layout.addWidget(self._files_list,5,0,1,2)
        self._main_layout.addWidget(self._preview_file_button,6,0)
        self._main_layout.addWidget(self._save_file_button,6,1)

        self._main_layout.addWidget(self._ok_button,7,0,1,2)

        self.setLayout(self._main_layout)

    def _make_config_model(self):
        # model 
        self._config_model = QtGui.QStandardItemModel()
        self._config_list.setModel(self._config_model)

        # iterate over config keys, fill model
        for key in sorted(self._experiment.get_config_fields()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self._config_model.appendRow(item)

        self._config_list.selectionModel().currentChanged.connect(self._slot_show_config_data)
        self._config_list.selectionModel().select(self._config_model.createIndex(0,0),QtCore.QItemSelectionModel.Select)

    def _make_entry_model(self):
        # model 
        self._entry_model = QtGui.QStandardItemModel()
        self._entry_list.setModel(self._entry_model)

        # iterate over entry keys, fill model
        for key in sorted(self._experiment.get_details().keys()):
            item = QtGui.QStandardItem(key)
            item.setEditable(False)
            self._entry_model.appendRow(item)

        self._entry_list.selectionModel().currentChanged.connect(self._slot_show_entry_data)
        self._entry_list.selectionModel().select(self._entry_model.createIndex(0,0),QtCore.QItemSelectionModel.Select)

    def _make_files_model(self):
        self._files_model = QtGui.QStandardItemModel()
        self._files_list.setModel(self._files_model)

        self._files_list.activated.connect(self._slot_display_preview)

        # iterate over entry keys, fill model
        if self._filesystem is not None:
            # sources
            exp_dict = self._experiment.get_details()['experiment']
            base_dir = exp_dict['base_dir'] if 'base_dir' in exp_dict else None
            mainfile = exp_dict['mainfile'] if 'mainfile' in exp_dict else None
            sources = exp_dict['sources'] if 'sources' in exp_dict else None

            if mainfile in sources:
                pos = sources.index(mainfile)
                del sources[pos]
                item = QtGui.QStandardItem('Main file: ' + mainfile)
                item.setEditable(False)
                mainfilename = mainfile if base_dir is None else os.path.join(base_dir,mainfile)
                item.setData(mainfilename,FilenameRole)
                self._files_model.appendRow(item)

            for source in sources: # mainfile probably missing
                item = QtGui.QStandardItem(source[0])
                item.setEditable(False)
                sourcefilename = source[0] if base_dir is None else os.path.join(base_dir,source[0])
                item.setData(sourcefilename,FilenameRole)
                self._files_model.appendRow(item)

        self._files_list.selectionModel().selectionChanged.connect(self._update_preview_buttons)

    def _update_preview_buttons(self):
        selected_indexes = self._files_list.selectedIndexes()
        assert len(selected_indexes) <= 1
        if len(selected_indexes) == 0:
            self._preview_file_button.setEnabled(False)
            self._save_file_button.setEnabled(False)
        else:
            self._preview_file_button.setEnabled(True) # TODO stupid
            self._save_file_button.setEnabled(True)

    def _slot_show_config_data(self,index):
        this_key = str(self._config_model.data(index))
        this_config_data = self._experiment.get_field((BrowserState.Fields.FieldType.Config,this_key))
        self._config_display.setPlainText(str(this_config_data))

    def _slot_show_entry_data(self,index):
        this_key = str(self._entry_model.data(index))
        this_detail_data = self._experiment.get_details()[this_key]
        self._entry_display.setPlainText(str(this_detail_data))

    def _slot_display_preview(self):
        # double-click on file
        self._display_preview()

    def _slot_preview_button_clicked(self):
        self._display_preview()

    def _save_request(self):
        self._try_save_file()


    def _slot_save_button_clicked(self):
        self._try_save_file()

    # returns current file name (without dirrectory) and data
    def _get_current_file_data(self):
        selected_indexes = self._files_list.selectedIndexes()
        assert len(selected_indexes) <= 1
        if len(selected_indexes) == 0:
            return None

        the_index = selected_indexes[0]
        the_item = self._files_model.itemFromIndex(the_index)
        filename = the_item.data(FilenameRole)
        basename = os.path.basename(filename)

        data = self._filesystem.get_file(filename)
        decoded_data = data.decode('utf-8', 'backslashreplace')
        return (basename,decoded_data)

    def _display_preview(self):
        basename_and_data = self._get_current_file_data()
        if basename_and_data is None:
            return
        else:
            basename,data = basename_and_data

        display_dialog = QtWidgets.QDialog()
        display_dialog.setWindowTitle('Display attachment ' + basename)

        text_field = QtWidgets.QTextEdit()
        text_field.setPlainText(data)
        text_field.setReadOnly(True)

        save_button = QtWidgets.QPushButton('&Save')
        save_button.clicked.connect(self._save_request)

        ok_button = QtWidgets.QPushButton('&Ok')
        ok_button.clicked.connect(display_dialog.accept)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(text_field)
        layout.addWidget(save_button)
        layout.addWidget(ok_button)
        display_dialog.setLayout(layout)
        display_dialog.exec_()

    def _try_save_file(self):
        basename_and_data = self._get_current_file_data()
        if basename_and_data is None:
            return
        else:
            basename,data = basename_and_data

        last_save_directory = self._app.settings.value('Global/lastSaveDirectory')
        if last_save_directory is None:
            last_save_directory = os.getcwd()

        save_preset = os.path.join(last_save_directory,basename)
        save_file_name = QtWidgets.QFileDialog.getSaveFileName(caption='Save file attachment',directory = save_preset)[0]
        # note that the dialog will warn against overwriting

        if len(save_file_name) == 0:
            return #aborted

        dir_name = os.path.dirname(str(save_file_name))
        self._app.settings.setValue('Global/lastSaveDirectory',dir_name)

        print('Will now save to',save_file_name)
        fp = open(save_file_name,'wt') # TODO always assumes text?
        print(data,file=fp)
        fp.close()



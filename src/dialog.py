# QGIS Core
from qgis.core import QgsApplication
from qgis.core import QgsMapLayerProxyModel
from qgis.core import QgsProject
from qgis.core import QgsSettings
from qgis.core import QgsUnitTypes

# QGIS Utils
from qgis.utils import iface

# PyQt
from PyQt5           import uic
from PyQt5.Qt        import QStandardItem
from PyQt5.QtCore    import QDir 
from PyQt5.QtCore    import QModelIndex
from PyQt5.QtGui     import QFont
from PyQt5.QtGui     import QStandardItemModel
from PyQt5.QtWidgets import QFileSystemModel
from PyQt5.QtWidgets import QHeaderView
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QMenu

# Python
from math import isnan
import os

# Plugin
from .input_check import InputCheck
from .utils       import est_degree_error

# Loads the .ui file
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'dialog_ui', 'dialog_base.ui'))

class PluginDialog(QDialog, FORM_CLASS):
    def __init__(self, parent = None):
        """Constructor."""
        super(PluginDialog, self).__init__(parent)

        self.iface = iface
        self.msg   = self.iface.messageBar()
        self.qapp  = QgsApplication.instance()
        self.chk   = InputCheck()

        # Style setup
        self.setupUi(self)
        # This increases loadtime by 10x!!!
        # self.qapp.setStyle('Fusion')

        style = os.path.join(os.path.dirname(__file__), 'dialog_ui', 'stylesheet.qss')
        with open(style,"r") as s:
            self.setStyleSheet(s.read())

        # Read Settings
        s = QgsSettings()
        self.SOURCE_LYR_NAME  = s.value("GetFeats/sourceLayer", "Roads")
        self.TARGET_LYR_NAME  = s.value("GetFeats/targetLayer", "target_layer")
        self.CUSTOM_PREP_FILE = s.value("GetFeats/customPrepFile", "custom_prep.py")

        SRC_FIELDS0     = s.value("GetFeats/sourceFields", "NULL, NAME, TYPE")
        OUT_FIELDS      = s.value("GetFeats/outputFields", "Heading, Name, Type")
        MAX_DISTANCE    = s.value("GetFeats/maxDistance",  500)
        NEIGHBORS       = s.value("GetFeats/nNeighbors",   50)
        USE_CUSTOM_PREP = s.value("GetFeats/customPrep",   True)
        SELECT_FEATS    = s.value("GetFeats/selectFeats",  True)
        TBL_FONT_SIZE   = s.value("GetFeats/fontSpinBox",  10)

        # Set values from settings
        self.sourceFields.setText(SRC_FIELDS0)
        self.outputFields.setText(OUT_FIELDS)
        self.maxDistance.setValue(int(MAX_DISTANCE))
        self.nNeighbors.setValue(int(NEIGHBORS))
        self.customPrep.setChecked(bool(USE_CUSTOM_PREP))
        self.selectFeats.setChecked(bool(SELECT_FEATS))
        self.fontSpinBox.setValue(int(TBL_FONT_SIZE))

        # Filter ComboBox layers
        self.sourceLayer.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.sourceLayer.setShowCrs(True)
        self.targetLayer.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.targetLayer.setShowCrs(True)

        # Add link to custom_prep directory
        fpath    = os.path.join(os.path.dirname(__file__), 'custom_prep')
        path_str = '- <a href =' + fpath + '><span style="color:lightskyblue;">Link to directory</span></a>'
        self.customPrepLink.setText(path_str)
        self.customPrepLink.setToolTip(fpath)
        self.customPrepLink.setOpenExternalLinks(True)

        # Init custom prep file picker
        self.fsm = QFileSystemModel()
        index    = self.fsm.setRootPath(fpath)
        self.fsm.setFilter(QDir.Files|QDir.NoDotAndDotDot)
        self.fsm.setNameFilters(['*.py']) 
        self.customPrepFile.setModel(self.fsm)
        self.customPrepFile.setRootModelIndex(index)
        self.customPrepFile.setCurrentIndex(1)

        # Init the data table
        self.model = QStandardItemModel()
        self.tableView.setModel(self.model)
        self.tableView.horizontalHeader().setStretchLastSection(False)
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.model.setHorizontalHeaderLabels(self.extract_outfields())
        self.selection_model = self.tableView.selectionModel()
        self.set_table_font()
        self.update_table_panel_lbls()


        ###################
        ### Connections ###
        ###################
        # Set up the dialog pages
        self.pageMenu.currentRowChanged['int'].connect(self.stackedWidget.setCurrentIndex)

        # Update the custom prep info
        self.fsm.directoryLoaded.connect(self.on_custom_prep_dir_loaded)

        # Update table column names based on output fields in config
        self.outputFields.textChanged.connect(self.update_outfields)

        # Update the data table
        self.fontSpinBox.valueChanged.connect(self.set_table_font)

        # Update the labels on the table panel
        self.activatePlugin.stateChanged.connect(self.update_table_panel_lbls)
        self.enableCopyPaste.stateChanged.connect(self.update_table_panel_lbls)

        # Save only custom prep script choice
        self.saveCustomPrep.clicked.connect(lambda: self.save_custom_prep())
        
        # Connect the Menu/Done buttons
        self.showMenu.clicked.connect(self.show_menu)
        self.pb_close.clicked.connect(lambda: self.on_close())


    ###############
    ### Methods ###
    ###############  
    def on_custom_prep_dir_loaded(self, directory):
        parentIndex = self.fsm.index(directory)
        fnames = [self.fsm.index(i, 0, parentIndex).data() for i in range(self.fsm.rowCount(parentIndex))]
        if len(set(fnames)) == len(fnames) and fnames:
            self.customPrepFile.setEnabled(True)
            self.customPrep.setEnabled(True)
            self.saveCustomPrep.setEnabled(True)
            self.customPrep.setText('Use Custom Prep')
        else:
            self.customPrepFile.setEnabled(False)
            self.customPrep.setChecked(False)
            self.customPrep.setEnabled(False)
            self.saveCustomPrep.setEnabled(False)
            self.customPrep.setText('Use Custom Prep (Disabled: Check directory for valid .py files)')

        last_fname = self.CUSTOM_PREP_FILE
        if last_fname in fnames:
            idx = fnames.index(last_fname)
            self.customPrepFile.setCurrentIndex(idx)

    def set_table_font(self):
        font_size = self.fontSpinBox.value()
        self.tableView.setFont(QFont("Ubuntu", font_size))

    def show_menu(self):
        if self.showMenu.isChecked():
            self.pageMenu.setVisible(True)
            self.showMenu.setText(">>>") 
        else:
            self.pageMenu.setVisible(False)
            self.showMenu.setText("<<<")


    def contextMenuEvent(self, event):
        page_flag   = self.stackedWidget.currentIndex() == 2
        active_flag = self.enableCopyPaste.isChecked() and self.activatePlugin.isChecked()
        if not active_flag and page_flag and self.selection_model.selection().indexes():
            for i in self.selection_model.selection().indexes():
                row, column = i.row(), i.column()
            menu = QMenu()
            copyAction = menu.addAction("Copy Selected Cell")
            action = menu.exec_(self.mapToGlobal(event.pos()))
            if action == copyAction:
                val = self.tableView.model().item(row, column).text()
                self.qapp.clipboard().setText(val)

    def extract_sourcefields(self):
        return [x.strip() for x in self.sourceFields.text().split(',')]

    def extract_outfields(self):
        return [x.strip() for x in self.outputFields.text().split(',')]

    def update_outfields(self):
        self.model.setHorizontalHeaderLabels(self.extract_outfields())

    def update_table(self, OUT_FIELDS, features):
        self.model.setRowCount(0)
        self.model.setColumnCount(0)
        self.model.setHorizontalHeaderLabels(OUT_FIELDS)
        for feat in features:
            self.model.appendRow([QStandardItem(str(x)) for x in feat.attributes()])

    def save_settings(self):
        if self.chk.check_dialog_lyrs_exist(self):
            TARGET_LYR_NAME = self.targetLayer.currentLayer().name()
            SOURCE_LYR_NAME = self.sourceLayer.currentLayer().name()
            source_lyr = self.chk.check_lyr_valid(SOURCE_LYR_NAME)
            target_lyr = self.chk.check_lyr_valid(TARGET_LYR_NAME)
            if source_lyr and target_lyr:
                s = QgsSettings()
                s.setValue("GetFeats/sourceLayer",    self.sourceLayer.currentLayer().name())
                s.setValue("GetFeats/targetLayer",    self.targetLayer.currentLayer().name())
                s.setValue("GetFeats/sourceFields",   self.sourceFields.text())
                s.setValue("GetFeats/outputFields",   self.outputFields.text())
                s.setValue("GetFeats/maxDistance",    self.maxDistance.value())
                s.setValue("GetFeats/nNeighbors",     self.nNeighbors.value())
                s.setValue("GetFeats/customPrep",     self.customPrep.isChecked())
                s.setValue("GetFeats/customPrepFile", self.customPrepFile.currentText())
                s.setValue("GetFeats/selectFeats",    self.customPrep.isChecked())
                s.setValue("GetFeats/fontSpinBox",    self.fontSpinBox.value())
    
                self.msg.pushInfo('GetFeats:', 'Settings Saved')

    def save_custom_prep(self):
        s = QgsSettings()
        s.setValue("GetFeats/customPrepFile", self.customPrepFile.currentText())
        self.msg.pushInfo('GetFeats:', 'Custom Prep Saved')

    def update_table_panel_lbls(self):
        if self.activatePlugin.isChecked():
            self.pluginActiveLabel.setText("Active")
            self.pluginActiveLabel.setStyleSheet("QLabel { font: bold; color : #b7b0ff; }")
        else:
            self.pluginActiveLabel.setText("Inactive")
            self.pluginActiveLabel.setStyleSheet("QLabel { color : #777; }")
    
        if self.enableCopyPaste.isChecked() and self.activatePlugin.isChecked():
            self.copyPasteActiveLabel.setText("Active")
            self.copyPasteActiveLabel.setStyleSheet("QLabel { font: bold; color : #b7b0ff; }")
        else:
            self.copyPasteActiveLabel.setText("Inactive")
            self.copyPasteActiveLabel.setStyleSheet("QLabel { color : #777; }")


    def update_nnNotes(self):
        if self.activatePlugin.isChecked() and self.chk.check_dialog_lyrs_exist(self):
            SOURCE_LYR_NAME = self.sourceLayer.currentLayer().name()
            source_lyr      = self.chk.check_lyr_valid(SOURCE_LYR_NAME)
            if source_lyr:
                source_lyr_crs = source_lyr.crs()
                src_units = QgsUnitTypes.toString(source_lyr_crs.mapUnits())
                if src_units == 'meters':
                    self.nnNotes.setText('No unit conversion required')
                else:
                    pre_redi = '<span style=" font-weight:300; font-style:italic; color:#ff774a;">'
                    pre_blue = '<span style=" font-weight:600; font-style:bold;   color:#b7b0ff;">'
                    pre_bold = '<span style=" font-weight:600; font-style:bold;">'
                    suf     = '</span>'
                    self.nnNotes.setText('Converting ' + pre_bold + src_units + suf + ' to meters')
                if src_units == 'degrees':
                    max_dist = self.maxDistance.value()
                    if isnan(source_lyr.extent().yMinimum()):
                        lat = 45
                    else:
                        lat = max([abs(source_lyr.extent().yMinimum()), 
                                   abs(source_lyr.extent().yMaximum())])
                    deg_err  = est_degree_error(lat, max_dist)
                    deg_msg = ' - Consider reprojecting ' + pre_bold + SOURCE_LYR_NAME + suf + ' to a linear coordinate system'
                    self.nnNotes.append(pre_redi + deg_msg + suf)
                    self.nnNotes.append('')
                    self.nnNotes.append('Estimated ' + pre_bold + 'Max Distance' + suf + ' error:')
                    self.nnNotes.append(pre_blue + ' - Lat' + suf + ': ' + pre_bold + str(deg_err[0]) + suf + ' m')
                    self.nnNotes.append(pre_blue + ' - Lon' + suf + ': ' + pre_bold + str(deg_err[1]) + suf + ' m')

    def on_close(self):
        self.activatePlugin.setChecked(False)
        self.close()

    def closeEvent(self, event):
        self.on_close()

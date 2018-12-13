# This file contains the controller which manages interaction between the user, the database, and the
# different models. Most functions of the controller are called by the application in response to user commands.
# The controller is also responsible for creating a variety of models (DbModel.py and StateModels.py), and
# for setting up the dependencies between objects, i.e. to connect the respective changed() signals of objects to dependent objects.
# In the case of settings which are not covered by the QT model/view framework, the controller might update GUI 
# elements directly (open for refactoring)

from . import DbModel
from . import StateModels
from . import BrowserState
from . import Utilities

from PyQt5 import QtCore, QtGui, QtWidgets

class DbController(QtCore.QObject):
    
    ################## Initialization ##################
    def __init__(self,app,main_win,connection,browser_state,sorted_experiment_list):
        super().__init__(None)
        # save parameters
        self._app = app
        self._main_win = main_win
        self._browser_state = browser_state 
        self._sorted_experiment_list = sorted_experiment_list
        self._connection = connection

        self._create_models()

        # Now everything is built. 
        
        # 1) Connect models
        self._main_win.study_tree.setModel(self._study_tree_model)
        self._main_win.field_choice.set_models(self._invisible_fields_model,self._visible_fields_model)
        self._main_win.experiment_list_view.setModel(self._experiment_list_model)

        # 2) Connect self signals (might not all be necessary)

        self._browser_state.current_study.study_about_to_be_changed.connect(self.slot_study_about_to_be_changed)
        self._browser_state.current_study.study_changed.connect(self.slot_study_changed)

        self._browser_state.sort_order.sort_order_changed.connect(self.slot_sort_order_changed)

        self._browser_state.fields.invisible_fields_changed.connect(self.slot_invisible_fields_changed)
        self._browser_state.fields.visible_fields_changed.connect(self.slot_visible_fields_changed)

        self._browser_state.db_filter.filter_changed.connect(self.slot_new_filter) # TODO bad naming

        # TODO should this be done by the state model?
        self._browser_state.fields.visible_fields_to_be_changed.connect(self._visible_fields_model.slot_visible_fields_to_be_changed)
        self._browser_state.fields.visible_fields_changed.connect(self._visible_fields_model.slot_visible_fields_changed)
        self._browser_state.fields.invisible_fields_to_be_changed.connect(self._invisible_fields_model.slot_invisible_fields_to_be_changed)
        self._browser_state.fields.invisible_fields_changed.connect(self._invisible_fields_model.slot_invisible_fields_changed)

        # connection directly related to widgets
        self._browser_state.general_settings.view_mode_changed.connect(self.slot_view_mode_changed)
        self._browser_state.general_settings.column_width_changed.connect(self.slot_column_width_changed)
        self._browser_state.db_filter.filter_changed.connect(self._app._main_win.filter_choice.slot_filter_changed)
        self._browser_state.db_filter.filter_rejected.connect(self._app._main_win.filter_choice.slot_filter_rejected)


    def _create_models(self):
        self._study_tree_model = DbModel.StudyTreeModel(self._connection)
        self._experiment_list_model = DbModel.ExperimentListModel(self._browser_state,self._sorted_experiment_list)
        self._invisible_fields_model = StateModels.InvisibleFieldsModel(self._browser_state.fields)
        self._visible_fields_model = StateModels.VisibleFieldsModel(self._browser_state.fields)

    def set_connection(self,new_connection):
#         self._connection = new_connection
#         self._rebuild_models()
        raise Exception('TODO, but do not change the model')

    ################## Get data or models (public interface) ##################
    def get_study_tree_model(self):
        return self._study_tree_model

    def get_experiment_list_model(self):
        return self._experiment_list_model

    def get_available_fields_model(self):
        return self._available_fields_model

    def get_visible_fields_model(self):
        return self._visible_fields_model

    ################## Reactive functions (public interface) ##################
    def on_select_sacred_element(self):
        print('on_select_sacred_element!!!')
        # access study tree to find the current selection
        selected_indexes = self._main_win.study_tree.selectedIndexes()
        assert len(selected_indexes) <= 1
        if len(selected_indexes) == 0:
            return
        
        sacred_item = self._study_tree_model.sacred_from_index(selected_indexes[0])
        print('on_select_sacred_element!!!, ite is',sacred_item)
        if sacred_item.typename() == 'SacredDatabase':
            self._on_select_database(sacred_item)
        elif sacred_item.typename() == 'SacredStudy':
            self._on_select_study(sacred_item)
        else:
            raise Exception('Unexpected sacred item with typename %s' % sacred_item.typename())



    def reload_connection(self):
        raise Exception('not implemented')

    def delete_experiments(self,ob_ids):
#         print('Controller: now deleting experiments',ob_ids)
        self._browser_state.current_study.get_study().delete_experiments_from_database(ob_ids)

        current_filter_dict = self._browser_state.db_filter.get_filter_dict()

        self._browser_state.current_study.get_study().load(current_filter_dict)
        
    
    def field_add(self):
        # TODO possible make controller independent from main win, add fields to mehtod signature
        inv_selected_row = self._main_win.field_choice.get_invisible_fields_selected_row()
        vis_selected_row = self._main_win.field_choice.get_visible_fields_selected_row()
#         print('Controller: field_add called with selected rows %s, %s ' % (inv_selected_row,vis_selected_row))

        if vis_selected_row is None:
            vis_selected_row = 0

        self._browser_state.fields.add_visible(inv_selected_row,vis_selected_row)

    def field_remove(self):
        inv_selected_row = self._main_win.field_choice.get_invisible_fields_selected_row()
        vis_selected_row = self._main_win.field_choice.get_visible_fields_selected_row()
#         print('Controller: field_remove called with selected rows %s, %s ' % (inv_selected_row,vis_selected_row))

        assert vis_selected_row is not None

        self._browser_state.fields.remove_visible(vis_selected_row)

    def field_up(self):
        inv_selected_row = self._main_win.field_choice.get_invisible_fields_selected_row()
        vis_selected_row = self._main_win.field_choice.get_visible_fields_selected_row()
#         print('Controller: field_up called with selected rows %s, %s ' % (inv_selected_row,vis_selected_row))

        assert vis_selected_row is not None

        self._browser_state.fields.move_up(vis_selected_row)

    def field_down(self):
        inv_selected_row = self._main_win.field_choice.get_invisible_fields_selected_row()
        vis_selected_row = self._main_win.field_choice.get_visible_fields_selected_row()
#         print('Controller: field_down called with selected rows %s, %s ' % (inv_selected_row,vis_selected_row))

        assert vis_selected_row is not None

        self._browser_state.fields.move_down(vis_selected_row)

    def new_query(self,text):
#         print('CONTROLLER: new query')
        self._browser_state.db_filter.try_set_filter_text(text)
        # if the text is malformed, the browser state will not be changed

    def set_view_mode(self,mode):
        self._browser_state.general_settings.set_view_mode(mode)

    def sort_request(self,field,pos):
        self._browser_state.sort_order.sort_request(field,pos)

#     # Stuff related to the experiment list view
#     def get_experiment_details(self,sacred_experiment):
#         pass
#     # TODO

    def reload_experiment(self,exp):
        exp.load()


    ################## Actors which directly change widgets ##################

    # Update the status of the view mode radio buttons
    def update_view_mode_buttons(self):
        current_view_mode = self._browser_state.general_settings.get_view_mode()
        # TODO refactor this
        self._main_win.result_view_raw.setChecked(current_view_mode == BrowserState.GeneralSettings.ViewModeRaw)
        self._main_win.result_view_round.setChecked(current_view_mode == BrowserState.GeneralSettings.ViewModeRounded)
        self._main_win.result_view_percent.setChecked(current_view_mode == BrowserState.GeneralSettings.ViewModePercent)


    
    ################## Slots to be called from the state holders and database objects ##################
    def slot_study_about_to_be_changed(self,study):
        pass

    def slot_study_changed(self,study):
        # activate controls
        self._main_win.enable_study_controls(study is not None)
    
    def slot_experiment_list_changed(self):
        # This is called when the list of experiments has been reloaded
        pass

    def slot_invisible_fields_changed(self,visible,change_data):
        pass

    def slot_visible_fields_changed(self,visible,change_data):
        pass

    def slot_sort_order_changed(self,order_was_reset):
        pass

    def slot_column_width_changed(self,field,width):
        print('DBCONTROLLER - column_widths_changed')
        try:
            col_idx = self._browser_state.fields.get_visible_fields().index(field)
        except ValueError:
            print('BAD - column with name %s not found,, sync issue???' % str(field))
            return

        print('GOOD - field %s at position %d set to width %d' % (field,col_idx,width))
        self._main_win.experiment_list_view.setColumnWidth(col_idx,width)
        

    def slot_view_mode_changed(self,new_mode):
        self.update_view_mode_buttons()

    def slot_new_filter(self,filter_text,filter_dict):
        study = self._browser_state.current_study.get_study()
        if study is not None:
            study.load(filter_dict)

    ################## Internal functionality ##################
    def _on_select_database(self,database):
        # TODO reload?
        database.load_if_uninitialized()
        # this creates all signals to update views (I hope)

         

    def _on_select_study(self,study):
        # TODO reload?
        study.load_if_uninitialized()

        self._browser_state.current_study.set_study(study)


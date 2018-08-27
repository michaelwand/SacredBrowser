# This class contains structures which represent the state of the application (at a given time) which is NOT
# contained in the database.
# Change requests are usually initiated by a) a signal from a dependency, b) a method call from the controller.
# Each class sends signals to notify users of data changes. (TODO dependency management)

# Note that all classes should be treated as singletons. When the current study (or another dependency) is changed,
# the object contents are reset, but the object itself must NOT be deleted. All classes save their own state to the global
# QT settings object.

from PyQt5 import QtCore

import collections
import enum
import bisect

BrowserStateCollection = collections.namedtuple('BrowserStateCollection',['current_study','sort_order','db_filter','fields','general_settings'])

# Current study
class CurrentStudy(QtCore.QObject):
    study_about_to_be_changed = QtCore.pyqtSignal(object) # passes the OLD study, allows to disconnect signals etc.
    # TODO don't like that...
    study_changed = QtCore.pyqtSignal(object) # passed the NEW study

    def __init__(self):
        super().__init__()
        self._study = None

    def set_study(self,new_study):
        self.study_about_to_be_changed.emit(self._study)
        self._study = new_study
        self.study_changed.emit(new_study)

    def get_study(self):
        return self._study


# Order according to which experiments are shown (updated via the sorting dialog, and when a new
# study is loaded)
class SortOrder(QtCore.QObject):
    sort_order_to_be_changed = QtCore.pyqtSignal() # new order, was reset
    sort_order_changed = QtCore.pyqtSignal(list,bool) # new order, was reset

    def __init__(self):
        super().__init__()
        self._available_fields = []
        self._order = [] # order as list, a subset of _available_fields

    def set_available_fields(self,fields,reset=False):
        print('SORT ORDER: fields now',fields)
        self.sort_order_to_be_changed.emit()
        self._available_fields = fields
        if reset:
            self._order = []
        else:
            # reuse old order as much as possible
            new_order = [ x for x in self._order if x in self._available_fields ]
            self._order = new_order

        self.sort_order_changed.emit(self._order,reset)

    def on_sort_request(self,field,pos):
        assert field in self._available_fields

        self.sort_order_to_be_changed.emit()

        # Change existing order as little as possible. Three cases:
        # 1) field is not in list
        # 2) field is already in list, a) before or b) after the new position

        try:
            old_pos = self._order.index(field)
            # case 2)
            del self._order[old_pos]
            self._order.insert(pos,field)
#             if old_pos < pos:
#                 del self._order[old_pos] 
#                 self._order.insert(pos,field)
#             elif old_pos > pos:
#                 del self._order[old_pos]
#                 self._order.insert(pos,field)
        except ValueError:
            # case 1
            self._order.insert(pos,field)
            del self._order[-1]

        self.sort_order_changed.emit(self._order,False)

    def get_order(self):
        return self._order

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed

    def slot_study_changed(self,study):
        print('CALL TO SortOrder.slot_study_changed')
        pass # done by slot_visible_fields_changed

    def slot_visible_fields_changed(self,visible,change_data):
        self.set_available_fields(visible,reset=change_data.tp == Fields.ChangeType.Reset) # likewise emits change signal


# Last valid database filter request (updated whenever a new database query is made)
class DbFilter(QtCore.QObject):
    filter_to_be_changed = QtCore.pyqtSignal()
    filter_changed = QtCore.pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._filter_text = ''

    def set_filter_text(self,t):
        self.filter_to_be_changed.emit()
        self._filter_text = t
        self.filter_changed.emit(t)

    def get_filter_text(self):
        return self._filter_text

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed

    def slot_study_changed(self,study):
        print('CALL TO DbFilter.slot_study_changed')
        self.set_filter_text('') # TODO load ffrom storage

# Lists of fields which are displayed in the main experiment list, and which could be displayed but are not.
# Note that each field is a tuple (name,fieldtype).
class Fields(QtCore.QObject):
    # this is not a very readable class, due to the preparations for the QT models (which are not very simple either)

    # we might show config fields and result fields (extendable)
    class FieldType:
        Config = 1
        Result = 2

    # The following signals are intended for the model (a subclass of QAbstractListModel). The change type
    # is self-explaining, the info is 
    # - None in the case of Reset
    # - the changed rows in the case of Content
    # - (position, count) in the case of insert (insert happens BEFORE position, position == len(fields before insert)
    #   means that insert was performed at the end
    # - (position, count) in the case of delete (position is the first row deleted)
    # After the change, the new fields list is also passed
    class ChangeType(enum.Enum):
        Reset = 1
        Content = 2
        Insert = 3
        Remove = 4
    ChangeData = collections.namedtuple('ChangeData',['tp','info'])

    visible_fields_to_be_changed = QtCore.pyqtSignal(ChangeData)
    visible_fields_changed = QtCore.pyqtSignal(list,ChangeData)
    invisible_fields_to_be_changed = QtCore.pyqtSignal(ChangeData)
    invisible_fields_changed = QtCore.pyqtSignal(list,ChangeData)

    def __init__(self):
        super().__init__()
        self._invisible_fields = []
        self._visible_fields = []

    def set_fields(self,invisible=None,visible=None,force_reset=False):
        # This might be called when new data is loaded, or the study is changed, or fields  are
        # loaded from storage. force_reset forces "reset change" signals to be emitted even if
        # the data itself did not change. Note that other functions also change the list of fields.

        # Note the structure of the field lists
        if invisible is not None:
            for x in invisible:
                assert len(x) == 2
        if visible is not None:
            for x in visible:
                assert len(x) == 2

        visible_fields_changed = force_reset or (visible is not None)
        invisible_fields_changed = force_reset or (invisible is not None)

        # emit reset signals
        change_data = self.ChangeData(self.ChangeType.Reset,None)

        if visible_fields_changed:
            self.visible_fields_to_be_changed.emit(change_data)
        if invisible_fields_changed:
            self.invisible_fields_to_be_changed.emit(change_data)

        # perform changes
        if visible is not None:
            self._visible_fields = visible
        if invisible is not None:
            # sort by field type first (so results come at the end)
            self._invisible_fields = sorted(invisible)

#         print('SET FIELDS: vis =',self._visible_fields,' and invis = ',self._invisible_fields)

        if visible_fields_changed:
            self.visible_fields_changed.emit(self._visible_fields,change_data)
        if invisible_fields_changed:
            self.invisible_fields_changed.emit(self._invisible_fields,change_data)

    def get_available_fields(self):
        return self._invisible_fields + self._visible_fields

    def get_invisible_fields(self):
        return self._invisible_fields

    def get_visible_fields(self):
        return self._visible_fields

    def available_fields_count(self):
        return len(self._invisible_fields) + len(self._visible_fields)

    def invisible_fields_count(self):
        return len(self._invisible_fields)

    def visible_fields_count(self):
        return len(self._visible_fields)

    def move_up(self,vis_row):
        if vis_row < 1 or vis_row >= len(self._visible_fields):
            return # silently ignore?

        # this function changes the visible fields, required this way to get selection right
        change_data_remove = self.ChangeData(self.ChangeType.Remove,(vis_row - 1,1))
        self.visible_fields_to_be_changed.emit(change_data_remove)
        moved_field = self._visible_fields[vis_row - 1]
        del self._visible_fields[vis_row - 1]
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_remove)

        change_data_insert = self.ChangeData(self.ChangeType.Insert,(vis_row,1))
        self.visible_fields_to_be_changed.emit(change_data_insert)
        self._visible_fields.insert(vis_row,moved_field)
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_insert)

#         # this function changes the visible fields
#         change_data = self.ChangeData(self.ChangeType.Content,[vis_row-1,vis_row])
#         self.visible_fields_to_be_changed.emit(change_data)
# 
#         self._visible_fields[vis_row - 1],self._visible_fields[vis_row] = self._visible_fields[vis_row],self._visible_fields[vis_row-1]
#         self.visible_fields_changed.emit(self.get_visible_fields(),change_data)

    def move_down(self,vis_row):
        if vis_row < 0 or vis_row >= (len(self._visible_fields) - 1):
            return # silently ignore?

        # this function changes the visible fields, required this way to get selection right
        change_data_remove = self.ChangeData(self.ChangeType.Remove,(vis_row + 1,1))
        self.visible_fields_to_be_changed.emit(change_data_remove)
        moved_field = self._visible_fields[vis_row + 1]
        del self._visible_fields[vis_row + 1]
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_remove)

        change_data_insert = self.ChangeData(self.ChangeType.Insert,(vis_row,1))
        self.visible_fields_to_be_changed.emit(change_data_insert)
        self._visible_fields.insert(vis_row,moved_field)
        self.visible_fields_changed.emit(self.get_visible_fields(),change_data_insert)

    def add_visible(self,inv_row,where = None):
        field = self._invisible_fields[inv_row]

        # both lists are going to be changed
        invisible_change_data = self.ChangeData(self.ChangeType.Remove,(inv_row,1))
        visible_change_data = self.ChangeData(self.ChangeType.Insert,(where if where is not None else len(self._visible_fields),1))

        self.invisible_fields_to_be_changed.emit(invisible_change_data)
        self.visible_fields_to_be_changed.emit(visible_change_data)

        del self._invisible_fields[inv_row]
        if where is None:
            self._visible_fields.append(field)
        else:
            self._visible_fields.insert(where,field)

        print('add_visible, vis now',self._visible_fields)
        self.invisible_fields_changed.emit(self.get_invisible_fields(),invisible_change_data)
        self.visible_fields_changed.emit(self.get_visible_fields(),visible_change_data)

    def remove_visible(self,vis_row):
        field = self._visible_fields[vis_row]
        where = bisect.bisect(self._invisible_fields,field) 

        # both lists are going to be changed
        visible_change_data = self.ChangeData(self.ChangeType.Remove,(vis_row,1))
        invisible_change_data = self.ChangeData(self.ChangeType.Insert,(where,1))

        self.invisible_fields_to_be_changed.emit(invisible_change_data)
        self.visible_fields_to_be_changed.emit(visible_change_data)

        self._invisible_fields.insert(where,field)
        del self._visible_fields[vis_row]

        self.invisible_fields_changed.emit(self.get_invisible_fields(),invisible_change_data)
        self.visible_fields_changed.emit(self.get_visible_fields(),visible_change_data)

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed


    def slot_study_changed(self,study):
        # give the fields the format (type, field), this allows to sort naturally
        config_fields = [ (Fields.FieldType.Config, x) for x in study.list_config_fields() ]
        result_fields = [ (Fields.FieldType.Result, x) for x in study.list_result_fields() ]
        self.set_fields(config_fields + result_fields)

# Some general settings, note that they depend on the current study (much like everything else)

class GeneralSettings(QtCore.QObject):
    view_mode_to_be_changed = QtCore.pyqtSignal(int) # new view mode
    view_mode_changed = QtCore.pyqtSignal(int) # new view mode

    column_widths_to_be_changed = QtCore.pyqtSignal(int) # field, new width
    column_widths_changed = QtCore.pyqtSignal(int,int) # field, new width

    ViewModeRaw = 0
    ViewModeRounded = 1
    ViewModePercent = 2

    DefaultColumnWidth = 50

    def __init__(self):
        super().__init__()
        self._view_mode = self.ViewModeRounded
        self._column_widths = {}

    def get_view_mode(self):
        return self._view_mode

    def set_view_mode(self,new_mode):
        self.view_mode_to_be_changed.emit(new_mode)
        self._view_mode = new_mode
        self.view_mode_changed.emit(new_mode)

    def get_column_width(self,field):
        return self._column_widths.get(field,DefaultColumnWidth)

    def set_column_width(self,field,width):
        self.column_widths_to_be_changed.emit(field,width)
        self._column_widths[field] = width
        self.column_widths_changed.emit(field,width)

    def slot_study_about_to_be_changed(self,study):
        pass # done by slot_fields_changed

    def slot_study_changed(self,study):
        self.set_view_mode(self.ViewModeRounded)
        self._column_widths = {}
        # TODO load from storage, in particular the columns


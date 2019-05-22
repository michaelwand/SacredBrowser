# This file implements a sorted list of experiments. It takes input signals from Browserstate.SortOrder and
# BrowserState.CurrentStudy, as well as from the respective current study object.

from . import BrowserState
from . import DbEntries
from . import Utilities

from PyQt5 import QtCore

import functools
import numbers

ChangeType = Utilities.ChangeType
ChangeData = Utilities.ChangeData

# This is an item which can be sorted and supports comparing types (see _get_sort_pos_by_type)
@functools.total_ordering
class SortItem:
    def __init__(self,val):
        self._val = val

    def __eq__(self,other):
        try:
            return self._val == other._val
        except TypeError:
            return False

    @staticmethod
    def _get_sort_pos_by_type(val):
        if val is None:
            return 0
        if isinstance(val,str):
            return 1
        if isinstance(val,numbers.Number):
            return 2
        else:
            return 3

    def __le__(self,other):
        try:
            return self._val <= other._val
        except TypeError:
            my_pos = self._get_sort_pos_by_type(self._val)
            other_pos = self._get_sort_pos_by_type(other._val)
            return my_pos <= other_pos

# TODO add docs
class SortedExperimentList(QtCore.QObject):
    list_to_be_changed = QtCore.pyqtSignal(ChangeData)
    list_changed = QtCore.pyqtSignal(ChangeData)

    # Public interface
    def __init__(self,browser_state):
        super().__init__()
        self._browser_state = browser_state # also used to obtain current study

        self._slot_experiments_to_be_changed_closure = self._slot_experiments_to_be_changed
        self._slot_experiments_changed_closure = self._slot_experiments_changed
#         self._slot_study_deleted_closure = self._slot_study_deleted

        # make persistent connections
        self._browser_state.current_study.study_to_be_changed.connect(self._slot_study_to_be_changed)
        self._browser_state.current_study.study_changed.connect(self._slot_study_changed)
        self._browser_state.sort_order.sort_order_to_be_changed.connect(self._slot_sort_order_to_be_changed)
        self._browser_state.sort_order.sort_order_changed.connect(self._slot_sort_order_changed)

        # the list which is the main output of this class
        pre_change_emit = lambda cd: self.list_to_be_changed.emit(cd)
        post_change_emit = lambda cd: self.list_changed.emit(cd)
        loader = lambda obid: obid
        deleter = lambda exp: None
        self._sorted_experiments = Utilities.ObjectHolder(pre_change_emit=pre_change_emit,post_change_emit=post_change_emit,loader=loader,deleter=deleter)

    # Yields output
    def get_sorted_experiments(self):
        return [ self._browser_state.current_study.get_study().get_experiment(obid)[1] for obid in self._sorted_experiments.list_keys() ]

    def get_sorted_experiment_at(self,pos):
        return self._browser_state.current_study.get_study().get_experiment(self._sorted_experiments.get_by_position(pos)[0])[1]

    # Signal receivers
    def _slot_study_to_be_changed(self):
        old_study = self._browser_state.current_study.get_study()
        if old_study is not None:
            old_study.experiments_to_be_changed.disconnect(self._slot_experiments_to_be_changed_closure)
            old_study.experiments_changed.disconnect(self._slot_experiments_changed_closure)

    def _slot_study_changed(self):
        new_study = self._browser_state.current_study.get_study()
        if new_study is not None:
            new_study.experiments_to_be_changed.connect(self._slot_experiments_to_be_changed_closure)
            new_study.experiments_changed.connect(self._slot_experiments_changed_closure)

    def _slot_sort_order_to_be_changed(self):
        pass

    def _slot_sort_order_changed(self):
        self._resort()

    def _slot_experiments_to_be_changed(self,study,change_data):
        pass

    def _slot_experiments_changed(self,study,change_data):
        self._resort()

    # get list of all experiments, sort, and merge using the ObjectHolder
    def _resort(self):
        current_study = self._browser_state.current_study.get_study()
        if current_study is not None:
            exp_list = self._browser_state.current_study.get_study().get_all_experiments()
        else:
            exp_list = []
        sort_order = self._browser_state.sort_order.get_order()
        new_sorted_list = self._sort_exp_list(exp_list,sort_order)
        self._sorted_experiments.update(new_sorted_list)


    # Sort the list of experiments accoring to the given order. Returns the IDs of the sorted experiments.
    @staticmethod
    def _sort_exp_list(exp_list,order):
        # make a list which is suitable for sorting
        filtered_exp_data = []
        for exp in exp_list:
            this_item = []
            for k in order:
                try:
                    this_el = exp.get_field(k)
                except KeyError:
                    this_el = None
                this_item.append(SortItem(this_el))
            # finally append the ID, which is not important for sorting, but we need it later on
            # to indentify our experiments
            this_item.append(exp.id())
            filtered_exp_data.append(this_item)

        # perform sorting
        filtered_exp_data.sort()

        return [ x[-1] for x in filtered_exp_data ]




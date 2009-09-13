# ###################################################
# Copyright (C) 2009 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################
import weakref
import pychan

import horizons.main

from tabinterface import TabInterface
from horizons.util import Callback
from horizons.constants import RES, SETTLER
from horizons.gui.widgets.tooltip import TooltipButton
from horizons.command.production import ToggleActive

class OverviewTab(TabInterface):

	def __init__(self, instance, widget = 'tab_widget/tab_overview.xml'):
		super(OverviewTab, self).__init__(widget)
		self.instance = instance
		self.init_values()
		self.button_up_image = 'content/gui/images/icons/hud/common/building_overview_u.png'
		self.button_active_image = 'content/gui/images/icons/hud/common/building_overview_a.png'
		self.button_down_image = 'content/gui/images/icons/hud/common/building_overview_d.png'
		self.button_hover_image = 'content/gui/images/icons/hud/common/building_overview_h.png'
		self.tooltip = u"Overview"

	def refresh(self):
		"""This function is called by the TabWidget to redraw the widget."""
		if hasattr(self.instance, 'name'):
			self.widget.child_finder('name').text = unicode(self.instance.name)
		if hasattr(self.instance, 'health'):
			self.widget.child_finder('health').text = unicode(self.instance.health)
		self.widget.adaptLayout()

	def show(self):
		super(OverviewTab, self).show()
		if not self.instance.has_change_listener(self.refresh):
			self.instance.add_change_listener(self.refresh)
		if not self.instance.has_remove_listener(self.hide):
			self.instance.add_remove_listener(self.hide)

	def hide(self):
		super(OverviewTab, self).hide()
		if self.instance.has_change_listener(self.refresh):
			self.instance.remove_change_listener(self.refresh)
		if self.instance.has_remove_listener(self.hide):
			self.instance.remove_remove_listener(self.hide)


class BranchOfficeOverviewTab(OverviewTab):

	def __init__(self, instance):
		super(BranchOfficeOverviewTab, self).__init__(
			widget = 'tab_widget/tab_branch_overview.xml',
			instance = instance
		)
		self.button_up_image = 'content/gui/images/icons/hud/common/building_overview_u.png'
		self.button_active_image = 'content/gui/images/icons/hud/common/building_overview_a.png'
		self.button_down_image = 'content/gui/images/icons/hud/common/building_overview_d.png'
		self.button_hover_image = 'content/gui/images/icons/hud/common/building_overview_h.png'
		self.tooltip = u"Branch Office \\n Overview"

class ShipOverviewTab(OverviewTab):

	def __init__(self, instance):
		super(ShipOverviewTab, self).__init__(
			widget = 'tab_widget/tab_overview_ship.xml',
			instance = instance
		)
		self.button_up_image = 'content/gui/images/icons/hud/common/ship_inv_u.png'
		self.button_active_image = 'content/gui/images/icons/hud/common/ship_inv_a.png'
		self.button_down_image = 'content/gui/images/icons/hud/common/ship_inv_d.png'
		self.button_hover_image = 'content/gui/images/icons/hud/common/ship_inv_h.png'
		self.widget.findChild(name='name').stylize("headline")
		self.tooltip = u"Ship Overview"

	def refresh(self):
		# show rename when you click on name
		events = {
			'name': Callback(horizons.main.session.ingame_gui.show_change_name_dialog, self.instance)
		}

		# check if we can display the foundSettlement-anchor
		islands = horizons.main.session.world.get_islands_in_radius(self.instance.position, self.instance.radius)
		if len(islands) > 0:
			events['foundSettelment'] = Callback(horizons.main.session.ingame_gui._build, \
			                                     1, weakref.ref(self.instance) )
			self.widget.child_finder('bg_button').set_active()
			self.widget.child_finder('foundSettelment').set_active()
		else:
			events['foundSettelment'] = None
			self.widget.child_finder('bg_button').set_inactive()
			self.widget.child_finder('foundSettelment').set_inactive()

		self.widget.mapEvents(events)
		super(ShipOverviewTab, self).refresh()



class ProductionOverviewTab(OverviewTab):

	def  __init__(self, instance):
		super(ProductionOverviewTab, self).__init__(
			widget = 'buildings_gui/production_building_overview.xml',
			instance = instance
		)
		events = { 'toggle_active': ToggleActive(self.instance).execute }
		self.widget.mapEvents(events)
		self.button_up_image = 'content/gui/images/icons/hud/common/building_overview_u.png'
		self.button_active_image = 'content/gui/images/icons/hud/common/building_overview_a.png'
		self.button_down_image = 'content/gui/images/icons/hud/common/building_overview_d.png'
		self.button_hover_image = 'content/gui/images/icons/hud/common/building_overview_h.png'
		self.tooltip = u"Production Overview"

		self.destruct_button = TooltipButton(name="destruct_button", up_image="content/gui/images/background/delete.png", down_image="content/gui/images/background/delete_h.png", hover_image="content/gui/images/background/delete_h.png", tooltip="Destroy Building", position=(190,280))
		self.widget.addChild(self.destruct_button)
		self.widget.mapEvents({
			'destruct_button' : self.destruct_building
		})

	def refresh(self):
		"""This function is called by the TabWidget to redraw the widget."""
		costs = 0
		if hasattr(self.instance, 'running_costs'):
			costs = self.instance.running_costs
		self.widget.child_finder('running_costs').text = unicode(costs)
		super(ProductionOverviewTab, self).refresh()

	def destruct_building(self):
		horizons.main.session.ingame_gui.hide_menu()
		if self.destruct_button.gui.isVisible():
			self.destruct_button.hide_tooltip()
		self.instance.destruct_building()

class SettlerOverviewTab(OverviewTab):
	def  __init__(self, instance):
		super(SettlerOverviewTab, self).__init__(
			widget = 'tab_widget/tab_overview_settler.xml',
			instance = instance
		)
		self.tooltip = u"Settler Overview"
		self.consumed_res_icons = []

	def refresh(self):
		self.widget.child_finder('happiness').text = \
				unicode(self.instance.inventory[RES.HAPPINESS_ID]) + u'/100'
		self.widget.child_finder('inhabitants').text = unicode( "%s/%s" % ( \
			self.instance.inhabitants, self.instance.inhabitants_max ) )
		self.widget.child_finder('level').text = unicode(self.instance.level)
		self.widget.child_finder('taxes').text = unicode(self.instance.last_tax_payed)
		self.update_consumed_res()
		super(SettlerOverviewTab, self).refresh()

	def update_consumed_res(self):
		"""Updates the container that displays the needed resources of the settler"""
		container = self.widget.findChild(name="needed_res")
		# remove icons from the container
		for icon in self.consumed_res_icons:
			container.removeChild(icon)
		self.consumed_res_icons = [] # clear list

		# create new ones
		for res in self.instance.get_consumed_resources():
			icon = pychan.widgets.Icon()
			icon.image = horizons.main.db("SELECT icon FROM resource WHERE id = ?", res)[0][0]
			container.addChild(icon)
			self.consumed_res_icons.append(icon)

		container.adaptLayout()

class MarketPlaceOverviewTab(OverviewTab):

	def  __init__(self, instance):
		super(MarketPlaceOverviewTab, self).__init__(
			widget = 'tab_widget/tab_overview_marketplace.xml',
			instance = instance
		)
		self.tooltip = u"Market Place Overview"
		self.widget.distributeInitialData({'tax_list' : [ str(s) for s in SETTLER.TAX_SETTINGS ]})

	def refresh(self):
		self.widget.child_finder('tax_list').capture(self.on_tax_widget_change)
		super(MarketPlaceOverviewTab, self).refresh()

	def on_tax_widget_change(self):
		new_tax_num = self.widget.collectData('tax_list')
		self.instance.settlement.tax_setting = SETTLER.TAX_SETTINGS_VALUES[new_tax_num]

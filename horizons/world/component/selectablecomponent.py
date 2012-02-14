# ###################################################
# Copyright (C) 2012 The Unknown Horizons Team
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

from fife import fife
import copy

import horizons.main

from horizons.world.component import Component
from horizons.util import decorators
from horizons.constants import GFX, LAYERS

class SelectableComponent(Component):
	"""Stuff you can select.
	Has to be subdivided in buildings and units, which is further specialised to ships.

	Provides:
	show_menu(): shows tabs
	select(): highlight instance visually
	deselect(): inverse of select

	show_menu() and select() are frequently used in combination.

	The definitions must contain type, tabs and enemy_tabs.
	"""

	NAME = "selectablecomponent"

	@classmethod
	def get_instance(cls, arguments):
		# this can't be class variable because the classes aren't defined when
		# it would be parsed
		TYPES = { 'building' : SelectableBuildingComponent,
		          'unit'     : SelectableUnitComponent,
		          'ship'     : SelectableShipComponent }
		arguments = copy.copy(arguments)
		t = arguments.pop('type')
		return TYPES[ t ]( **arguments )

	def __init__(self, tabs, enemy_tabs):
		super(SelectableComponent, self).__init__()
		# resolve tab
		from horizons.gui import tabs as tab_classes
		resolve_tab = lambda tab_class_name : getattr(tab_classes, tab_class_name)
		self.tabs = map(resolve_tab, tabs)
		self.enemy_tabs = map(resolve_tab, enemy_tabs)

	def show_menu(self, jump_to_tabclass=None):
		"""Shows tabs from self.__class__.tabs, if there are any.
		@param jump_to_tabclass: open the first tab that is a subclass to this parameter
		"""
		from horizons.gui.tabs import TabWidget
		tablist = None
		if self.instance.owner == self.session.world.player:
			tablist = self.tabs
		else: # this is an enemy instance with respect to the local player
			tablist = self.enemy_tabs

		if tablist:
			tabs = [ tabclass(self.instance) for tabclass in tablist if
			         tabclass.shown_for(self.instance) ]
			tabwidget = TabWidget(self.session.ingame_gui, tabs=tabs)

			if jump_to_tabclass:
				num = None
				for i in xrange( len(tabs) ):
					if isinstance(tabs[i], jump_to_tabclass):
						num = i
						break
				if num is not None:
					tabwidget._show_tab(num)

			self.session.ingame_gui.show_menu( tabwidget )

	def select(self, reset_cam=False):
		raise NotImplementedError()
	def deselect(self):
		raise NotImplementedError()


class SelectableBuildingComponent(SelectableComponent):

	selection_color = (255, 255, 100)

	# these smell like instance attributes, but sometimes have to be used in non-instance
	# contexts (e.g. building tool).
	_selected_tiles = [] # tiles that are selected. used for clean deselect.
	_selected_fake_tiles = [] # fake tiles create over ocean to select (can't select ocean directly)

	def __init__(self, tabs, enemy_tabs, range_applies_only_on_island=True):
		super(SelectableBuildingComponent, self).__init__(tabs, enemy_tabs)

		self.range_applies_only_on_island = range_applies_only_on_island

	def initialize(self):
		# check for related buildings (defined in db, not yaml)
		related_building = self.session.db.get_related_building_ids(self.instance.id)
		if len(related_building) > 0:
			from horizons.gui.tabs import BuildRelatedTab
			self.tabs += (BuildRelatedTab,)

	def load(self, db, worldid):
		self.initialize()

	def select(self, reset_cam=False):
		"""Runs necessary steps to select the building."""
		self.set_selection_outline()
		if reset_cam:
			self.session.view.center(*self.instance.position.origin.to_tuple())
		renderer = self.session.view.renderer['InstanceRenderer']
		self._do_select(renderer, self.instance.position, self.session.world,
		                self.instance.settlement, self.instance.radius, self.range_applies_only_on_island)
		self._is_selected = True

	def set_selection_outline(self):
		"""Only set the selection outline.
		Useful when it has been removed by some kind of interference"""
		renderer = self.session.view.renderer['InstanceRenderer']
		renderer.addOutlined(self.instance._instance, self.selection_color[0], self.selection_color[1],
		                     self.selection_color[2], GFX.BUILDING_OUTLINE_WIDTH,
		                     GFX.BUILDING_OUTLINE_THRESHOLD)

	def deselect(self):
		"""Runs neccassary steps to deselect the building.
		Only deselects if this building has been selected."""
		if not hasattr(self, "_is_selected") or not self._is_selected:
			return # only deselect selected buildings (simplifies other code)
		self._is_selected = False
		renderer = self.session.view.renderer['InstanceRenderer']
		renderer.removeOutlined(self.instance._instance)
		renderer.removeAllColored()
		for fake_tile in self.__class__._selected_fake_tiles:
			self.session.view.layers[LAYERS.FIELDS].deleteInstance(fake_tile)
		del self.__class__._selected_fake_tiles[:] # delete inplace, assignment would operate on lowest class in hierarchy

	def remove(self):
		#TODO move this as a listener
		if self in self.session.selected_instances:
			self.session.selected_instances.remove(self)
		if self.instance.owner == self.session.world.player:
			self.deselect()
		super(SelectableBuildingComponent, self).remove()

	@classmethod
	def select_building(cls, session, position, settlement,
	                    radius, range_applies_only_on_island):
		"""Select a hypothecial instance of this class. Use Case: Buildingtool.
		Only works on a subclass of BuildingClass, since it requires certain class attributes.
		@param session: Session instance
		@param position: Position of building, usually Rect
		@param settlement: Settlement instance the building belongs to"""
		renderer = session.view.renderer['InstanceRenderer']

		"""
		import cProfile as profile
		import tempfile
		outfilename = tempfile.mkstemp(text = True)[1]
		print 'profile to ', outfilename
		profile.runctx( "cls._do_select(renderer, position, session.world, settlement)", globals(), locals(), outfilename)
		"""
		cls._do_select(renderer, position, session.world, settlement,
		               radius, range_applies_only_on_island)

	@classmethod
	def deselect_building(cls, session):
		"""@see select_building
		Used by building tool, allows incremental updates
		@return list of tiles that were deselected."""
		remove_colored = session.view.renderer['InstanceRenderer'].removeColored
		for tile in cls._selected_tiles:
			remove_colored(tile._instance)
			if tile.object is not None:
				remove_colored(tile.object._instance)
		selected_tiles = cls._selected_tiles
		del cls._selected_tiles[:] # delete inplace, assignment would operate on lowest class in hierarchy
		for fake_tile in cls._selected_fake_tiles:
			session.view.layers[LAYERS.FIELDS].deleteInstance(fake_tile)
		del cls._selected_fake_tiles[:] # delete inplace, assignment would operate on lowest class in hierarchy
		return selected_tiles

	@classmethod
	def _do_select(cls, renderer, position, world, settlement,
	               radius, range_applies_only_on_island):
		if range_applies_only_on_island:
			island = world.get_island(position.origin)
			if island is None:
				return # preview isn't on island, and therefore invalid

			ground_holder = None # use settlement or island as tile provider (prefer settlement, since it contains fewer tiles)
			if settlement is None:
				ground_holder = island
			else:
				ground_holder = settlement

			for tile in ground_holder.get_tiles_in_radius(position, radius, include_self=False):
				try:
					if ( 'constructible' in tile.classes or 'coastline' in tile.classes ):
						cls._add_selected_tile(tile, renderer)
				except AttributeError:
					pass # no tile or no object on tile
		else:
			# we have to color water too
			# since water tiles are huge, create fake tiles and color them

			if not hasattr(cls, "_fake_tile_obj"):
				# create object to create instances from
				cls._fake_tile_obj = horizons.main.fife.engine.getModel().createObject('fake_tile_obj', 'ground')
				fife.ObjectVisual.create(cls._fake_tile_obj)

				img_path = 'content/gfx/base/water/fake_water.png'
				img = horizons.main.fife.imagemanager.load(img_path)
				for rotation in [45, 135, 225, 315]:
					cls._fake_tile_obj.get2dGfxVisual().addStaticImage(rotation, img.getHandle())

			layer = world.session.view.layers[LAYERS.FIELDS]
			island = world.get_island(position.origin)
			# color island or fake tile
			for tup in position.get_radius_coordinates(radius):
				tile = island.get_tile_tuple(tup)
				if tile is not None:
					try:
						cls._add_selected_tile(tile, renderer)
					except AttributeError:
						pass # no tile or no object on tile
				else: # need extra tile
					inst = layer.createInstance(cls._fake_tile_obj,
					                            fife.ModelCoordinate(tup[0], tup[1], 0), "")
					fife.InstanceVisual.create(inst)

					cls._selected_fake_tiles.append(inst)
					renderer.addColored(inst, *cls.selection_color)

	@classmethod
	def _add_selected_tile(cls, tile, renderer):
		cls._selected_tiles.append(tile)
		renderer.addColored(tile._instance, *cls.selection_color)
		# Add color to objects on tht tiles
		renderer.addColored(tile.object._instance, *cls.selection_color)


class SelectableUnitComponent(SelectableComponent):

	def select(self, reset_cam=False):
		"""Runs necessary steps to select the unit."""
		self.session.view.renderer['InstanceRenderer'].addOutlined(self.instance._instance, 255, 255, 255, GFX.UNIT_OUTLINE_WIDTH, GFX.UNIT_OUTLINE_THRESHOLD)
		self.instance.draw_health()

	def deselect(self):
		"""Runs necessary steps to deselect the unit."""
		self.session.view.renderer['InstanceRenderer'].removeOutlined(self.instance._instance)
		self.instance.draw_health(remove_only=True)
		# this is necessary to make deselect idempotent
		if self.session.view.has_change_listener(self.instance.draw_health):
			self.session.view.remove_change_listener(self.instance.draw_health)


class SelectableShipComponent(SelectableUnitComponent):

	def select(self, reset_cam=False):
		"""Runs necessary steps to select the ship."""
		self.instance._selected = True
		super(SelectableShipComponent, self).select(reset_cam=reset_cam)

		# add a buoy at the ship's target if the player owns the ship
		if self.session.world.player == self.instance.owner:
			self.instance._update_buoy()

		if self.instance.owner is self.session.world.player:
			self.session.ingame_gui.minimap.show_unit_path(self.instance)

	def deselect(self):
		"""Runs necessary steps to deselect the ship."""
		self.instance._selected = False
		super(SelectableShipComponent, self).deselect()
		self.instance._update_buoy(remove_only=True)



decorators.bind_all(SelectableBuildingComponent)
decorators.bind_all(SelectableShipComponent)
decorators.bind_all(SelectableUnitComponent)
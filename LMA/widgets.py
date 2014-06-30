
from __future__ import print_function
from brawl4d.brawl4d import redraw
from brawl4d.LMA.controller import LMAController
from IPython.html import widgets # Widget definitions
from IPython.display import display # Used to display widgets in the notebook
from IPython.display import Javascript
from IPython.display import HTML

class LMAwidgetController:

	def __init__(self, panels, lma_ctrl, scatter_ctrl, charge_lasso, d): #, station_number_selection, charge_lasso_widget, draw_lasso_widget, color_field_widget, animation_time_widget, animate_button, label, LMA_Controlsa, LMA_Controlsb, tools_popup, number_of_stations):
		self.panels = panels
		self.lma_ctrl = lma_ctrl
		self.d = d
		self.scatter_ctrl = scatter_ctrl
		self.charge_lasso = charge_lasso
		
		#Max Chi2 Value:
		chi2_selection = widgets.BoundedFloatTextWidget(description='Max Chi2:', min='0.0', max='1000.0', value='1')
		chi2_selection.set_css({
			'max-width' : '30px',
		})
		chi2_selection.on_trait_change(self.max_chi2, 'value')
		
		
		#Station Number Selection:
		station_number_selection = widgets.DropdownWidget(description='Number of Stations:', 
				values=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], value=7)
		station_number_selection.set_css({
			'background-dropdown': '#888888',
			'color': 'white',
		})	
		station_number_selection.on_trait_change(self.number_of_stations, 'value')

		#Charge Lasso and Draw Button:
		charge_lasso_widget = widgets.RadioButtonsWidget(description='Charge Selection:', values=["-1", "0", "1"], value="-1")
		charge_lasso_widget.on_trait_change(self.change_lasso_charge, 'value')

		draw_lasso_widget = widgets.ButtonWidget(description='Draw')
		draw_lasso_widget.set_css({
			'background': '#888888',
			'color': 'white',
		})
		draw_lasso_widget.on_click(self.lasso_button) 

		#Color Field Selection:
		color_field_widget = widgets.RadioButtonsWidget(description='Color By:', values=["chi2", "time", "charge"], value="time")
		color_field_widget.on_trait_change(self.change_color_field, 'value')

		#Animate (Slider and Button) Optional Manual Numerical Input commented out:
		animation_time_widget = widgets.IntSliderWidget(description='Animation Time:', min='0', max='30')
		animation_time_widget.value = '5'
		# animation_time_widget = widgets.TextWidget(Description='Animation Time')
		# animation_time_widget.placeholder = "value"
		animate_button = widgets.ButtonWidget(description="Animate")
		animate_button.set_css({
			'display': 'flex',
			'align-content': 'flex-end',
			'background': '#888888',
			'color': 'white',
		})
		animate_button.on_click(self.run_animation_button)

		#FOR CONTAINERS AND POPUP
		label = widgets.LatexWidget(value='LMA Tools')
		label.set_css({
			'font-size': '20px',
			'font-weight': 'bold',
			'align-self': 'center',
			'padding': '15px',
			'background': 'd8d8d8',
		})

		LMA_Controlsa = widgets.ContainerWidget()
		LMA_Controlsa.children = [station_number_selection, charge_lasso_widget, draw_lasso_widget, chi2_selection]
		LMA_Controlsa.set_css({
			'display': 'flex',
			'flex-direction': 'column',
			# 'max-width': '300px',
			'flex-flow': 'row wrap',
			'align-content': 'flex-start',
			'padding': '10px',
			'background': '#e8e8e8',
			'font-weight': 'bold',
		})
		LMA_Controlsa.remove_class('vbox')
		LMA_Controlsa.add_class('hbox')

		LMA_Controlsb = widgets.ContainerWidget()
		LMA_Controlsb.children = [color_field_widget, animation_time_widget, animate_button]
		LMA_Controlsb.set_css({
			'display': 'flex',
			'flex-flow': 'wrap',
			'align-items': 'right',
			'columns': '1',
			'padding': '10px',
			'background': '#e8e8e8',
			'font-weight': 'bold',
		})
		LMA_Controlsb.remove_class('vbox')
		LMA_Controlsb.add_class('hbox')

		tools_popup = widgets.PopupWidget(description='LMA Control Hub')
		tools_popup.set_css({
			'font-size': '14px',
			'align-self': 'center',
			'padding': '15px',
			'border': '5px ridge #989898',
			'background': '#e8e8e8',

		})
		tools_popup.children = [label, LMA_Controlsa, LMA_Controlsb]
		
		self.chi2_selection = chi2_selection
		self.station_number_selection = station_number_selection
		self.charge_lasso_widget = charge_lasso_widget
		self.draw_lasso_widget = draw_lasso_widget
		self.color_field_widget = color_field_widget
		self.animation_time_widget = animation_time_widget
		self.animate_button = animate_button
		self.label = label
		self.LMA_Controlsa = LMA_Controlsa
		self.LMA_Controlsb = LMA_Controlsb
		self.tools_popup = tools_popup

#Where each widget is defined with their respective values:
	
	def max_chi2(self, name, value):
		self.lma_ctrl.bounds.chi2=(0,value)
		redraw(self.panels)
		
	def number_of_stations(self, name, value):
		self.lma_ctrl.bounds.stations=(value,99)
		redraw(self.panels)

	def change_lasso_charge(self, name, value):
		print(value)
		self.charge_lasso.charge=value

	def lasso_button(self, on_click):
		self.panels.lasso()

	def change_color_field(self, name, the_value):
		self.scatter_ctrl.color_field = the_value
		redraw(self.panels)

	def run_animation_button(self, anim):
		n_seconds = self.animation_time_widget.value
		anim=self.scatter_ctrl.animate(n_seconds, repeat=False)
		anim.repeat=False
		redraw(self.panels)		

		
	
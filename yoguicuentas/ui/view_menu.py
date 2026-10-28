"""Opciones de visualización independientes de los parámetros físicos."""
import tkinter as tk


def add_view_menu(menubar,canvas,edit_scale):
    menu=tk.Menu(menubar,tearoff=False)
    visible=tk.BooleanVar(master=menubar,value=canvas.colorbar_visible)
    menu.add_checkbutton(label='Barra de colores',variable=visible,
                         command=lambda:canvas.set_colorbar(visible.get()))
    menu.add_separator()
    menu.add_command(label='Ajustar escala de color…',command=edit_scale)
    menubar.add_cascade(label='Ver',menu=menu)
    return menu,visible

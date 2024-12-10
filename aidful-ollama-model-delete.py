#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
import subprocess
import tkinter.messagebox as messagebox
import tkinter.font as tkFont
import datetime
import re
import os

def check_ollama_installed():
    try:
        subprocess.check_output(['ollama', '--version'], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_installed_models():
    try:
        output = subprocess.check_output(['ollama', 'list'], universal_newlines=True)
        lines = output.strip().split('\n')
        models = []
        if len(lines) < 2:
            return models  # No models installed

        header_line = lines[0]
        # Find the starting index of each column based on the header positions
        name_pos = header_line.find('NAME')
        size_pos = header_line.find('SIZE')
        modified_pos = header_line.find('MODIFIED')

        for line in lines[1:]:
            if line.strip() == '':
                continue
            # Extract each field based on column positions
            full_name = line[name_pos:size_pos].strip()
            # Clean up the name to remove the hash
            name = full_name.split()[0]  # This will take just the "name:tag" part
            size = line[size_pos:modified_pos].strip()
            modified = line[modified_pos:].strip()
            models.append({'name': name, 'size': size, 'modified': modified})
        return models
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", "Failed to retrieve the list of models.")
        return []
    except FileNotFoundError:
        messagebox.showerror("Error", "Ollama command not found.")
        return []

def delete_selected_models(tree):
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select at least one model to delete.")
        return
    # Get the names of the selected models
    models_to_delete = []
    for item in selected_items:
        model_name = tree.item(item, 'values')[0].strip()  # Name is at index 0
        models_to_delete.append(model_name)
    # Confirm deletion
    confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the selected models?\n{', '.join(models_to_delete)}")
    if confirm:
        # Run 'ollama rm' command
        try:
            subprocess.check_call(['ollama', 'rm'] + models_to_delete)
            messagebox.showinfo("Success", "Selected models have been deleted.")
            # Refresh the model list
            refresh_model_list(tree)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"An error occurred while deleting the models: {e}")
        except FileNotFoundError:
            messagebox.showerror("Error", "Ollama command not found.")

def refresh_model_list(tree):
    # Clear the existing items
    for item in tree.get_children():
        tree.delete(item)
    # Fetch and display the models
    models = get_installed_models()
    for model in models:
        tree.insert('', tk.END, values=(model['name'], model['size'], model['modified']))

def select_all_models(select_all_var, tree):
    if select_all_var.get():
        tree.selection_set(tree.get_children())
    else:
        tree.selection_remove(tree.get_children())

def update_select_all(select_all_var, tree):
    if len(tree.selection()) == len(tree.get_children()):
        select_all_var.set(True)
    else:
        select_all_var.set(False)

def sort_by(tree, col, descending):
    # Get the data from the treeview
    data = [(tree.set(child, col), child) for child in tree.get_children('')]
    # If the column is 'Size', we need to parse the sizes into numbers
    if col == 'Size':
        def parse_size(size_str):
            size_str = size_str.strip().upper()
            match = re.match(r'([\d\.]+)\s*([KMG]?B)', size_str)
            if match:
                num, unit = match.groups()
                num = float(num)
                if unit == 'KB':
                    return num * 1024
                elif unit == 'MB':
                    return num * 1024 * 1024
                elif unit == 'GB':
                    return num * 1024 * 1024 * 1024
                else:
                    return num
            else:
                return 0  # Unknown size format
        data = [(parse_size(d[0]), d[1]) for d in data]
    elif col == 'Modified':
        def parse_date(date_str):
            try:
                # Adjust the date format according to your 'Modified' column format
                return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                return datetime.datetime.min  # Assign minimal date for unparseable dates
        data = [(parse_date(d[0]), d[1]) for d in data]
    else:
        data = [(d[0].lower(), d[1]) for d in data]

    # Now sort the data
    data.sort(reverse=descending)
    # Rearrange items in the treeview
    for index, (val, item) in enumerate(data):
        tree.move(item, '', index)
    # Switch the sort order for next time
    tree.heading(col, command=lambda: sort_by(tree, col, not descending))

def main():
    root = tk.Tk()
    root.title("aidful-ollama-model-delete")
    root.geometry("800x400")

    # Set the icon
    icon_path = os.path.join(os.path.dirname(__file__), "aidful-icon.png")
    icon = tk.PhotoImage(file=icon_path)
    root.iconphoto(True, icon)

    if not check_ollama_installed():
        messagebox.showerror("Ollama Not Found", "Ollama is not installed on your system. Please install Ollama and try again.")
        root.destroy()
        return

    # Create a frame for the Treeview
    tree_frame = ttk.Frame(root)
    tree_frame.pack(fill=tk.BOTH, expand=True)

    # Define font
    tree_font = tkFont.Font(family='Helvetica', size=12)

    # Create the Treeview
    columns = ('Name', 'Size', 'Modified')
    tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='extended')
    for col in columns:
        tree.heading(col, text=col, command=lambda _col=col: sort_by(tree, _col, False))
        tree.column(col, width=200)
    tree.pack(fill=tk.BOTH, expand=True)

    # Apply font to Treeview
    style = ttk.Style()
    style.configure('Treeview', rowheight=25, font=tree_font)
    style.configure('Treeview.Heading', font=('Helvetica', 8, 'bold'))

    # Fetch and display the models
    refresh_model_list(tree)

    # Create a frame for buttons and instructions
    bottom_frame = ttk.Frame(root)
    bottom_frame.pack(fill=tk.X, padx=10, pady=5)

    # Add Select All checkbox and Delete button to the left
    left_frame = ttk.Frame(bottom_frame)
    left_frame.pack(side=tk.LEFT)

    select_all_var = tk.BooleanVar()
    select_all_checkbox = tk.Checkbutton(left_frame, text='Select All', variable=select_all_var, command=lambda: select_all_models(select_all_var, tree))
    select_all_checkbox.pack(side=tk.LEFT)

    delete_button = ttk.Button(left_frame, text="Delete Selected Models", command=lambda: delete_selected_models(tree))
    delete_button.pack(side=tk.LEFT, padx=(10, 0))

    # Add instructions to the right
    instructions = ttk.Label(bottom_frame, text="Click on a column header to sort the list.\nScroll long lists with your mousewheel.\nSelect multiple models by clicking while holding CTRL", justify=tk.RIGHT)
    instructions.pack(side=tk.RIGHT)

    # Bind the selection event to update the checkbox
    tree.bind('<<TreeviewSelect>>', lambda e: update_select_all(select_all_var, tree))

    root.mainloop()

if __name__ == '__main__':
    main()

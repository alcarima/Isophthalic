import tkinter as tk

root = tk.Tk()
root.title("RGB Test")
root.geometry("400x400")

canvas = tk.Canvas(root, width=300, height=300, bg="white")
canvas.pack(pady=20)

canvas.create_oval(50, 50, 250, 250, fill="red", outline="black", width=2)

root.mainloop()
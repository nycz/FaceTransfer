#!/usr/bin/env python3

from datetime import datetime
import os.path
import sys
import tempfile
from tkinter import *
from tkinter.messagebox import *
from tkinter import filedialog
from tkinter.ttk import *

from common import GameError
import facetransfer

version = '0.1'


def get_save_path():
    """ Get the path to the Skyrim savegame folder, using some windoze magic """
    try:
        import ctypes.wintypes
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(0, 5, 0, 0, buf)
        return os.path.join(buf.value, 'My Games', 'Fallout4', 'Saves')
    except:
        return ''

def format_playing_time(timestamp):
    out = []
    # Fallout 4 timestamp (does not include seconds)
    if 'days' in timestamp:
        t = [x[:-1].lstrip('0') for x in timestamp.split('.', 3)[:3]] + ['']
    # Skyrim timestamp (does not include days)
    else:
        t = [''] + [x.lstrip('0') for x in timestamp.split('.')]
    if t[0]:
        out.append(t[0] + 'days')
    if t[1]:
        out.append(t[1] + 'h')
    if t[2]:
        out.append(t[2] + 'min')
    if t[3]:
        out.append(t[3] + 's')
    return ' '.join(out)


class MainWindow(Frame):
    def __init__(self, root):
        super().__init__(root)
        root.title('Fallout 4 Face Transfer')
        # Global~ish variables
        self.savedir = get_save_path()
        self.wildcard = [('Fallout 4 save files', '*.fos'),
                         #('Skyrim save files', '*.ess'),
                         ('All files', '*')]
        # Menu
        menubar = Menu(self)
        menu = Menu(menubar, tearoff=0)
        menu.add_command(label='About', command=self.show_about_dialog)
        #menu.add_command(label='Visit Nexus page')
        menu.add_command(label='Quit', command=lambda:root.destroy())
        menubar.add_cascade(label='Menu', menu=menu)
        root.config(menu=menubar)
        # Source/target box
        self.field = {}
        self.screen = {}
        self.widgets = {}
        self.screenshot = {}
        browsefuncs = {'source': self.source_browse, 'target': self.target_browse}
        for t in ('source', 'target'):
            self.field[t] = StringVar()
            self.widgets[t] = {}
            self.add_file_info_box(self, t, self.widgets[t], browsefuncs[t],
                                self.field[t])
            Frame(self, height=10).pack(side=TOP)

        # Bottom part
        self.btntransfer = Button(self, text='Transfer',
                                  command=self.execute_transfer)
        self.btntransfer.pack(side=RIGHT)
        # Warning labels
        self.warninglabelvar = StringVar()
        self.warninglabel = Label(root, textvariable=self.warninglabelvar)
        self.pack(fill=BOTH, expand=1, padx=8, pady=8)

    def add_file_info_box(self, mainframe, name, labeldict, btncallback, fvar):
        """
        Create and add a infobox containing the info about a loaded
        savegame.
        """
        title = {'source':'Copy face from source file:',
                 'target':'To target file:'}
        frame = LabelFrame(mainframe, text=title[name])
        frame.pack(anchor=N, fill=X, expand=1, side=TOP, padx=0, pady=0)
        frame.columnconfigure(1, weight=1)

        btn = Button(frame, text='Browse', command=btncallback)
        btn.grid(column=0, row=0, padx=2, pady=2)

        field = Entry(frame, width=50, textvariable=fvar)
        field.grid(column=1, row=0, columnspan=2, padx=2, pady=2, sticky=W+E)

        l = ('name','gender','level','race','location','save number','playing time')
        for n, (i, j) in enumerate([(x.capitalize()+':', x) for x in l]):
            Label(frame, text=i, state=DISABLED).grid(column=0, row=n+1, padx=4,
                                                      pady=3, sticky=E)
            labeldict[j] = StringVar()
            Label(frame, textvariable=labeldict[j]).grid(column=1, row=n+1,
                                                     padx=4, pady=3, sticky=W)
        self.screenshot[name] = Label(frame)
        self.screenshot[name].grid(column=2, row=1, rowspan=len(l),
                                   padx=4, pady=4)

    def show_about_dialog(self):
        import platform
        showinfo('About Face Transfer', 'Face Transfer {0} \n\n'
                 'Programmed in 2015 by nycz.\n\nLicensed under GPL. See the '
                 'sourcecode for more info.\n\nMade to run on Python 3.4 or '
                 'above.\n\nRunning on python version: {1}'
                 ''.format(version, platform.python_version()))

    def source_browse(self):
        self.browse('source')

    def target_browse(self):
        self.browse('target')

    def browse(self, t):
        fname = filedialog.askopenfilename(initialdir=self.savedir,
                                           filetypes=self.wildcard)
        if not fname:
            return
        fname = os.path.normpath(fname)
        try:
            info, game = facetransfer.get_ui_data(fname)
        except GameError as e:
            showerror('Error: format not recognized', str(e))
            return
        if game != 'fallout4':
            showerror('Error: wrong game', 'The file doesn\'t seem to be a Fallout 4 save file.')
            return
        self.field[t].set(fname)
        for k,v in info.items():
            if k == 'screenshot':
                w, h, shotdata = v
                if len(shotdata)/w/h == 4:
                    shotdata = bytes([b for n,b in enumerate(shotdata) if (n+1)%4 != 0])
                tfile = tempfile.NamedTemporaryFile('wb', suffix='.ppm',
                                                    delete=False)
                if h == 384:
                    rows = list(zip(*[iter(shotdata)]*w*3))
                    tempshotdata = []
                    for y in range(0, len(rows), 2):
                        for x in range(0, len(rows[0]), 6):
                            for n in [0,1,2]:
                                newval = int((rows[y][x+n] + rows[y][x+n+3] + rows[y+1][x+n] + rows[y+1][x+n+3])/4)
                                tempshotdata.append(newval)
                    shotdata = bytes(tempshotdata)
                    w, h = w//2, h//2
                with tfile:
                    tfile.write('P6\n{0} {1}\n255\n'.format(w,h).encode())
                    tfile.write(shotdata)
                img = PhotoImage(file=tfile.name)
                os.remove(tfile.name) # Remove the tempfile
                self.screenshot[t].config(image=img, relief=SUNKEN)
                self.screenshot[t].image = img
            elif k == 'playing time':
                self.widgets[t][k].set(format_playing_time(v))
            elif k == 'gender':
                self.widgets[t][k].set(['Male', 'Female'][v])
            else:
                self.widgets[t][k].set(v)

    def execute_transfer(self):
        if not self.field['target'].get() or not self.field['source'].get():
            showerror('Error: files missing', 'You have to pick a source and a target file.')
            return
        if self.widgets['target']['gender'].get() != self.widgets['source']['gender'].get():
            showerror('Error: different gender', 'Both saves must have the same player gender.')
            return
        if self.widgets['target']['race'].get() != self.widgets['source']['race'].get():
            showerror('Error: different race', 'Both saves must have the same player race.')
            return
        success = facetransfer.transfer_face(self.field['source'].get(),
                                             self.field['target'].get())
        if success:
            showinfo('Done', 'The face has been copied to the target file!')
        else:
            showerror('Oops', 'Something went wrong! Look at the error log.')


class ErrWrapper(object):
    """
    Good stuff! Generate a file with all errors not printed in the non-existing
    console window.
    """
    def __init__(self, realoutput, logfilename):
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)
        self.realoutput = realoutput
        self.logfilename = os.path.join(application_path, logfilename)

    def write(self, text):
        with open(self.logfilename, 'a') as f:
            f.write(text)
        self.realoutput.write(text)



if __name__=='__main__':
    errorlog = datetime.now().strftime('facetransfer_error_%Y-%m-%d_%H-%M-%S.txt')
    sys.stderr = ErrWrapper(sys.stderr, errorlog)
    root = Tk()
    MainWindow(root)
    root.mainloop()
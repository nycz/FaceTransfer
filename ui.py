#!/usr/bin/env python3

from tkinter import *
from tkinter.messagebox import *
from tkinter.ttk import *

version = '0.1'


class MainWindow(Frame):
    def __init__(self, root):
        super().__init__(root)
        root.title('Fallout 4 Face Transfer')
        # Menu
        menubar = Menu(self)
        menu = Menu(menubar, tearoff=0)
        menu.add_command(label='About', command=self.showAboutDialog)
        menu.add_command(label='Help', command=self.showHelpDialog)
        menu.add_command(label='Visit Nexus page')
        menu.add_command(label='Quit', command=lambda:root.destroy())
        menubar.add_cascade(label='Menu', menu=menu)
        root.config(menu=menubar)
        # Source/target box
        self.field = {}
        self.screen = {}
        self.widgets = {}
        self.screenshot = {}
        doBrowse = {'source': self.sourceBrowse, 'target': self.targetBrowse}
        for t in ('source', 'target'):
            self.field[t] = StringVar()
            self.widgets[t] = {}
            self.addFileInfoBox(self, t, self.widgets[t], doBrowse[t],
                                self.field[t])
            Frame(self, height=10).pack(side=TOP)

        # Bottom part
        self.btn_transfer = Button(self, text='Transfer', state=DISABLED)
        self.btn_transfer.pack(side=RIGHT)
        # Warning labels
        self.warninglabelvar = StringVar()
        self.warninglabel = Label(root, textvariable=self.warninglabelvar)
        self.pack(fill=BOTH, expand=1, padx=8, pady=8)

    def addFileInfoBox(self, mainframe, name, labeldict, btncallback, fvar):
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


    def showAboutDialog(self):
        import platform
        showinfo('About Skyrim Face Transfer', 'Skyrim Face Transfer {0} \n\n'
                 'Programmed in 2012 by nycz.\n\nLicensed under GPL. See the '
                 'sourcecode for more info.\n\nMade to run on Python 2.6 or '
                 'above (not Python 3).\n\nRunning on python version: {1}'
                 ''.format(version, platform.python_version()))

    def showHelpDialog(self):
        showinfo('Help (You should probably read the readme instead)',
                 "Skyrim Face Transfer lets you transfer your "
                 "character's face from one savefile to another. Just choose "
                 "the file with the face you want to reuse (the source), and "
                 "then the file with the character you want the face to go to. "
                 "\n\nIt is best if both characters are of the same race, "
                 "since the function to copy the race is currently bugged. "
                 "Even so, you are free to try it out anyway. Also, "
                 "transferring a face between characters with different race "
                 "and/or gender WITHOUT transferring the gender/race, may look "
                 "odd. (The target will have the facial traits of the source "
                 "gender/race, but still be the target's gender/race in every "
                 "other way).\n\nFinally, SFT creates a backup of the target "
                 "save before modifying it but if you want to be on the safe "
                 "side you are still recommended to backup your saves before "
                 "using this program.")

    def sourceBrowse(self):
        self.browse('source')

    def targetBrowse(self):
        self.browse('target')

    def browse(self, t):
        print('beep boop', t)

if __name__=='__main__':
    root = Tk()
    MainWindow(root)
    root.mainloop()
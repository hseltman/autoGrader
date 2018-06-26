"""
Created on Thu Jul 20 08:24:55 2017
ref: http://www.datadependence.com/2016/04/how-to-build-gui-in-python-3/
@author: Howard J. Seltman
"""
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
from tkinter import filedialog
from tkSimpleDialog import Dialog
# from tkinter.simpledialog import Dialog


class AutoGrader(ttk.Frame):
    """
    This class defines the AutoGrader GUI and functions.

    This program analyzes one or more sets of submitted homework files
    for a whole class.  An assignment is assumed to request one or more
    "codefiles".  Each codefile is a specific name and extension, and
    each student is expected to submit file(s) of the same exact names to
    the course management software.  It is assumed that course management
    software such as Canvas or Blackboard has altered the required code file
    name(s) by appending information such as student or group name,
    timestamp and version number.  The user then unzips the assignment
    files into a unique directory for that assignment.

    AutoGrader supports a complex configuration system.  Configuration
    occurs at the assignment level (e.g., course number, and file format
    from the course management system), which is called "general", and at
    the codefile level (e.g., specific text required in the codefile or its
    output), which is call "specific".  Defaults are hardcoded for both types.
    A global general file (AutoGrader.config) and/or a global specific
    configuration file (AutoGrader.specific.config) may be placed in the
    user's home directory or a directory specified by the system
    environmental variable "AUTOGRADER_GLOBAL_CONFIG".  Items in these
    files override any hardcoded defaults to become user defaults.

    When selecting a directory to work in, any items in the directory's
    general configuration file (AutoGrader.config) override the user's
    defaults for the current assignment.  An item labelled "General setup..."
    on the "Configuration" menu can be used to create and/or alter the
    general configuration file for the assignment.

    Specific configuration files labelled "foo.config", where "foo" is
    the name of a codefile (including extension) are maintained for each
    codefile.  Unless created in advance by the user, a specific configuration
    file is create for each codefile, based on the user's defaults, when
    the directory is initially selected.  The main AutoGrader dialog shows
    radio buttons for selecting the active codefile.  The "Configuration"
    menu has a "Setup foo..." item to change any configuration information
    for that file.

    The user analyzes submissions for one codefile at a time by selecting
    individual code files from a dropdown box or all student files for that
    code file.  A sandbox is setup for each student (shared across code files).

    Codefiles are analyzed before the code is submitted, then the code is
    submitted to the appropriate compile or interpreter, the warning
    and error messages are collected, and any output is analyzed to produce
    a report for each student / code file combination.  These can
    be combined into a per student aggregate report.

    Current acceptable codefiles are *.R, *.Rmd, *.RRmd (indicating either
    *.R or *.Rmd), *.sas, and *.py.
    """
    def __init__(self, parent, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.one_time_setup()
        self.setup_for_new_dir()
        self.init_gui()
        self.update_gui(new_codefiles=True, new_codefile_files=True)
        return

    def one_time_setup(self):
        """
        There are two configuration objects.  First is a general configuration
        dictionary called 'self.general_config' that applies to all codefiles
        in one directory and specifies the filename formats, which codefiles
        to analyze, etc.  Second is a dictionary containing a specific
        configuration dictionary for each codefile (specific up to the
        submitted file name, but covering all students) which defines the
        criteria for acceptable code for that codefile.

        The initial (hardcoded) definitions for each type of configuration
        dictionary is a tuple of tuples where each default configuration entry
        has "entry name", "entry label", "type" ('int', 'line', or 'box'),
        "dimensions" (columns or a tuple of rows and columns), and the
        "default value" (an integer or a string).  The configuration files
        that can be used to set or override the global configuration are
        plain text files that follow the format "id: value" where "id"
        matches on of the pre-specified "entry name" items and "value" is
        an appropriate value (integer or text on one or more lines).  Each
        "id: value" pair must be separated from the others by one or more
        blank lines.

        In the general configuration, the "file format" can include "%s" for
        student/group name, "%t" for time/date stamp info, "%e" for email,
        "%f" for filename, and "%j" for junk (to be discarded).  Any one other
        character is the literal separator.  E.g., the format for Canvas is
        "%s_%t_%f" because file names are constructed by prepending the
        student name (hyphenated), and a timestamp to the submitted file
        name, all separated by a pair of underscores.  (Canvas inserts "-#"
        between the end of the file name and the period indicating the
        file extention as version numbering when assignments are re-submitted,
        and AutoGrader understands that format.)

        Also in the general configuration files is a field called
        "codefiles" which is a comma-separated list of files the student
        was supposed to have submitted.  ".R" matches ".R" and ".r" files only.
        ".Rmd" matches ".Rmd" and ".rmd" files only.  ".RRmd" matches either.
        It is best to include specific file names before the ".R", ".Rmd", or
        ".RRmd" (and these will be case insensitive), but "*" is also allowed
        as the only entry, in which case AutoGrader will parse all available
        files. ".py" runs python 3.x.  ".sas" runs SAS.

        For the specific configuration files, the name(s) match the entries
        for "codefiles" in the general configuration dictionary, with
        ".config" appended, one per "filenames" entry.  These may be created
        manually, but if they are absent, AutoGrader will present a
        configuration window to obtain the information needed to create them.
        The items available include minimum number of comments, minimum number
        of comment lines, maximum number of warnings, maximum number of errors,
        required code lines, and required output lines.  The latter two are
        regular expressions.
        """
        import os
        import os.path
        import re

        # Misc. initializations
        self.general_config_fname = "AutoGrader.config"
        self.specific_config_fname = "AutoGrader.specific.config"
        self.valid_file_fields = "stfejl"  # [see one_time_setup()]
        self.max_codefiles = 10
        SAS_loc = os.environ.get("SAS_LOCATION")
        if SAS_loc is None:
            SAS_loc = "C:\Program Files\SasHome\SASFOUNDATION\9.4"
        self.SAS_prog = os.path.join(SAS_loc, "sas.exe")
        self.active_letter_file = None
        self.re_points = re.compile("^[{]([-+]?[0-9.]+?)[}][ ]*([^ ]+.*$)")

        # Allow environmental variable to set starting directory if no
        # configuration file is in the working directory.
        files = os.listdir()
        if "autoGrader.config" not in files:
            self.start_loc = os.environ.get("AUTOGRADER_STARTLOC")
            if self.start_loc is not None:
                try:
                    os.chdir(self.start_loc)
                except FileNotFoundError:
                    raise(Exception("Fix the Environmental Variable " +
                                    "'AUTOGRADER_STARTLOC' and try again"))

        # load configuration setups, each as a tuple of tuples
        self.general_config_setup = (
                 ('codefiles', 'Expected codefiles:', 'line', 60,
                  '*.RRmd'),
                 ('file_format', 'File format:', 'line', 30,
                  '%s_%t_%f'),
                 ('course_id', 'Course id:', 'line', 15, ''),
                 ('roster_name_col', 'Roster name column:', 'line', 40,
                  'Name'),
                 ('roster_firstname_col', 'Roster first name column:', 'line',
                  40, 'FirstName'),
                 ('roster_lastname_col', 'Roster last name column:', 'line',
                  40, 'LastName'),
                 ('roster_email_col', 'Roster email column:', 'line', 40,
                  'Email'),
                 ('filename_name_fmt', 'Filename name format:', 'line', 20,
                  'Last, First'),
                 ('email_suffix', 'Email suffix:', 'line', 30,
                  '@andrew.cmu.edu')
                )
        self.specific_config_setup = (
                 ('aux_files', 'Auxiliary files', 'box', (3, 40), ''),
                 ('min_comments', 'Min. comments:', 'int', None, 5),
                 ('min_blanks', 'Min. blanks:', 'int', None, 5),
                 ('max_warnings', 'Max. warnings:', 'int', None, 0),
                 ('max_errors', 'Max. errors:', 'int', None, 0),
                 ('req_code', 'Required code:', 'box', (4, 80), ''),
                 ('req_output', 'Required output:', 'box', (4, 80), ''),
                 ('prohib_code', 'Prohibited code:', 'box', (4, 80), ''),
                 ('prohib_output', 'Prohibited output:', 'box',
                  (4, 80), ''),
                 ('dropped_messages', 'Dropped messages:', 'box', (2, 80), ''),
                 ('pdf_output', 'Attempt pdf output (y/n):', 'line', 1, 'y'),
                 ('total_points', 'total_points', 'int', None, 100),
                 ('code_prepend', 'Code to prepend:', 'box', (3, 50), ''),
                 ('code_append', 'Code to append:', 'box', (3, 50), ''),
                )

        # Initialize global general configuration from setup tuple, then
        # replace any elements from global general configuration file (if
        # found).  Nate that later, a local general configuration file may
        # overwrite these.)
        env_loc = os.environ.get("AUTOGRADER_GLOBAL_CONFIG")
        global_loc = "~" if env_loc is None else env_loc
        self.global_general_config = \
            self.construct_config(self.general_config_setup)
        global_config_name = os.path.join(os.path.expanduser(global_loc),
                                          self.general_config_fname)
        if os.path.isfile(global_config_name):
            self.global_general_config = \
                self.update_config_from_file(global_config_name,
                                             self.global_general_config,
                                             self.general_config_setup)
        self.general_config = None

        # Initialize global specific configuration from setup tuple, then
        # replace any elements from global specific configuration file (if
        # found).  Nate that later, a local specific configuration file may
        # overwrite these.)
        self.global_specific_config = \
            self.construct_config(self.specific_config_setup)
        global_config_name = os.path.join(os.path.expanduser(global_loc),
                                          self.specific_config_fname)
        if os.path.isfile(global_config_name):
            self.global_specific_config = \
                self.update_config_from_file(global_config_name,
                                             self.global_specific_config,
                                             self.specific_config_setup)
        self.specific_configs = None

        # No codefiles are defined yet, so we point to nothing
        self.cf_index = None
        # file_format not yet decoded; roster not yet read
        self.filename_separator = None
        self.roster_id = None
        self.current_code = None
        return

    def set_file_format_info(self, file_format):
        """
        Read a 'file_format' and set self.filename_separator and
        self.file_format_items (file_format as a list).  Record
        if 'student_name' is in file format.
        """
        instructions = \
            "'File format must be constructed from one unique separator\n" + \
            "character and '%f' for filename, '%t' for time/date stamp,\n" + \
            "'%s' for student name, '%e' for email address, '%j' for\n" + \
            "junk (anything else), and '%l' for optional 'late'.  Email\n" + \
            "or student name is required."
        chars = set([x for x in file_format])
        seps = [x for x in chars if x not in "%" + self.valid_file_fields]

        sep = seps[0] if len(seps) == 1 else "_"
        fmt = file_format.split(sep)
        bad = [x[1:] not in self.valid_file_fields for x in fmt] or \
            fmt[0] == "%l"
        inadequate = '%s' not in fmt and '%e' not in fmt
        if len(seps) != 1 or len(fmt) < 2 or any(bad) or inadequate:
            messagebox.showwarning("Bad 'File format' in general setup",
                                   instructions)
            file_format = self.global_general_config['file_format']
            self.general_config['file_format'] = file_format
            self.write_config_file(self.general_config_fname,
                                   self.general_config)
            sep = '_'
            fmt = file_format.split(sep)
        self.filename_separator = sep
        self.file_format_items = fmt
        self.student_name_in_file_format = ('%s' in fmt)
        if '%l' in fmt:
            self.late_index_in_file_format = fmt.index('%l')
            self.file_format_items.remove('%l')
        else:
            self.late_index_in_file_format = -1
        return

    def construct_config(self, setup_tuple):
        """
        Construct a config dictionary from a tuple of tuples in the format
        specified in the comments on one_time_setup().
        Element order is  0=id, 1=label, 2=type, 3=dim, 4=default.
        """
        import time
        rslt = {}
        for i in range(len(setup_tuple)):
            this = setup_tuple[i]
            rslt[this[0]] = this[4]
        rslt['config_mod_time'] = time.time()
        return rslt

    def update_general_config(self):
        """
        Generate general configuration based on global general configuration
        and configuration file in the current (local) directory.
        """
        import os
        import copy
        old_file_format = self.general_config['file_format']
        old_course_id = self.general_config['course_id']
        self.general_config = copy.copy(self.global_general_config)
        local_config_name = os.path.join(self.dir, self.general_config_fname)
        if os.path.isfile(local_config_name):
            self.general_config = self.update_config_from_file(
                    local_config_name, self.general_config,
                    self.general_config_setup)
        if self.general_config['file_format'] != old_file_format or \
                self.filename_separator is None:
            ff = self.general_config['file_format']
            self.set_file_format_info(ff)
        if self.general_config['course_id'] != old_course_id or \
                self.roster_id is None:
            self.read_roster()
        return

    def read_roster(self):
        import os
        import re
        import pandas as pd
        if self.general_config['course_id'] == '':
            self.roster_firstname = None
            self.roster_lastname = None
            self.roster_email = None
            self.roster_fullname = None

        course = self.general_config['course_id']
        roster_re = re.compile(course + ".*[.]csv$", re.IGNORECASE)
        env_loc = os.environ.get("AUTOGRADER_GLOBAL_CONFIG")
        env_loc = os.path.expanduser("~" if env_loc is None else env_loc)
        candidates = []
        for file in os.listdir(env_loc):
            if roster_re.search(file) is not None:
                candidates.append(file)

        if len(candidates) == 0:
            self.roster_firstname = None
            self.roster_lastname = None
            self.roster_email = None
            self.roster_id = None
            self.roster_fullname = None
            return

        if len(candidates) == 1:
            candidate = os.path.join(env_loc, candidates[0])
        else:
            candidate = filedialog.askopenfilename(
                title="Select a roster for " + course,
                initialdir=env_loc, filetype=[("CSV File", "*.csv")])
            if candidate == '':
                self.roster_firstname = None
                self.roster_lastname = None
                self.roster_email = None
                self.roster_id = None
                self.roster_fullname = None
                return

        roster = pd.read_csv(candidate)

        # Read and store specific roster info
        self.roster_id = self.general_config['course_id']
        colnames = list(roster.columns.values)
        colname = self.general_config['roster_firstname_col']
        self.roster_firstname = None
        if colname != '':
            hascol = colnames.count(colname)
            if hascol > 0:
                self.roster_firstname = roster[colname].tolist()
        colname = self.general_config['roster_lastname_col']
        self.roster_lastname = None
        if colname != '':
            hascol = colnames.count(colname)
            if hascol > 0:
                self.roster_lastname = roster[colname].tolist()
        colname = self.general_config['roster_email_col']
        self.roster_email = None
        if colname != '':
            hascol = colnames.count(colname)
            if hascol > 0:
                self.roster_email = roster[colname].tolist()

        if self.roster_firstname is None or \
                self.roster_lastname is None:
            self.roster_fullname = None
        else:
            if self.general_config['filename_name_fmt'] == 'Last, First':
                self.roster_fullname = [b + ', ' + a for (a, b) in
                                        zip(self.roster_firstname,
                                            self.roster_lastname)]
            elif self.general_config['filename_name_fmt'] == 'Last.First':
                self.roster_fullname = [b + '.' + a for (a, b) in
                                        zip(self.roster_firstname,
                                            self.roster_lastname)]
            elif self.general_config['filename_name_fmt'] == 'First.Last':
                self.roster_fullname = [a + '.' + b for (a, b) in
                                        zip(self.roster_firstname,
                                            self.roster_lastname)]
            elif self.general_config['filename_name_fmt'] == 'FirstLast':
                self.roster_fullname = [a + b for (a, b) in
                                        zip(self.roster_firstname,
                                            self.roster_lastname)]
            elif self.general_config['filename_name_fmt'] == 'LastFirst':
                self.roster_fullname = [b + a for (a, b) in
                                        zip(self.roster_firstname,
                                            self.roster_lastname)]
            else:
                self.roster_fullname = [a + " " + b for (a, b) in
                                        zip(self.roster_firstname,
                                            self.roster_lastname)]
            # Make lower case for easy matching
            self.roster_fullname = [s.lower() for s in self.roster_fullname]

        # Remove @domain from emails
        self.roster_email = [re.sub("@.*", "", s.lower()) for s in
                             self.roster_email]
        return

    def set_specific_configs(self):
        """
        Generate self.specific_configs, a dictionary of specific configuration
        dictionaries, one for each codefile, based on specific configuration
        files found in the current directory or generated from user defaults
        (hardcoded and then overridded by any global specific configuration
        file).
        If any file does not exist, a default version is written to the
        current directory.
        Returns the dictionary of dictionaries
        """
        import copy
        self.specific_configs = {}
        for file in self.codefiles:
            specific_config_inner = copy.copy(self.global_specific_config)
            local_config_name = file + ".config"
            specific_config_inner = \
                self.update_config_from_file(local_config_name,
                                             specific_config_inner,
                                             self.specific_config_setup,
                                             write_if_missing=True)
            self.specific_configs[local_config_name] = \
                specific_config_inner
        return

    def update_config_from_file(self, fname, config_dict, config_setup,
                                write_if_missing=False):
        """
        Read text file 'fname' with items like 'id: value' with items possibly
        spanning several lines and with blank lines between items.  For each
        id that matches a config_setup 'id', store the value in config.dict.
        Return updated config.dict.
        """
        import time
        import os.path
        import re

        text = []
        try:
            fh = open(fname, 'r')
        except IOError:
            if not write_if_missing:
                messagebox.showwarning("Bad file", "Cannot open " + fname)
        else:
            text = fh.read()
            fh.close()

        if not text:
            config_dict['config_mod_time'] = time.time()
            self.write_config_file(fname, config_dict)
            return config_dict

        # Update config_dict from text in file
        file_mod_time = os.path.getmtime(fname)
        config_dict['config_mod_time'] = file_mod_time
        ids = [x[0] for x in config_setup]
        text = text.split("\n\n")
        text = [t for t in text if len(t) > 0]
        for line in text:
            re.header = re.compile("^\s*([a-zA-Z_0-9]+):\s*((.|\n)*)")
            colon = re.header.search(line)
            if colon is None:
                messagebox.showwarning("Bad file format",
                                       "Missing colon in " + fname)
                return
            id = colon.groups()[0]
            value = colon.groups()[1]
            if value == '':
                value = ' '
            if value[-1] == "\n":
                value = value[:-1]
            m = ids.count(id)
            if m != 1 and id != 'config_mod_time':
                messagebox.showwarning("Bad config info",
                                       "Invalid id '" + id + "' in " +
                                       fname)
            elif id == 'config_mod_time':
                pass
            else:
                m = ids.index(id)
                if config_setup[m][2] == 'int':
                    try:
                        config_dict[id] = int(value)
                    except ValueError:
                        messagebox.showwarning("Bad config. info",
                                               "In " + fname + ", " +
                                               config_setup[m][0] +
                                               " must be an integer.")
                elif config_setup[m][2] == 'box':
                    config_dict[id] = value
                elif config_setup[m][2] == 'line':
                    config_dict[id] = value
                else:
                    messagebox.showwarning("Error!", "bad config def.")
                    return
        return config_dict

    def write_config_file(self, fname, config_dict):
        with open(fname, 'w') as out:
            try:
                for id in config_dict.keys():
                    value = config_dict[id]
                    if type(value) is int or type(value) is float:
                        value = str(value)
                    out.write(id + ": " + value + '\n\n')
            except IOError:
                messagebox.showwarning("File write error",
                                       "Could not write " + fname)
        return

    def setup_for_new_dir(self):
        """
        Initialize self.general_config and self.specific_configs based on
        self.global_general_config, any general config file in the current
        directory, and 'codefiles' (possibly wildcard).
        """
        import os
        import copy

        self.dir = os.getcwd()
        self.general_config = copy.copy(self.global_general_config)
        self.update_general_config()
        self.get_codefiles()
        self.get_student_files(forceFirst=True)
        if len(self.student_name) == 0:
            self.current_code = None

        if self.codefiles is None:
            self.codefile = None
            self.codefile_index = 0
            self.specific_configs = None
            return

        self.codefile_index = 0
        if len(self.codefiles) > self.max_codefiles:
            messagebox.showwarning("Too many codefiles",
                                   "Too many codefiles: only using " +
                                   self.max_codefiles)
            self.codefiles = self.codefiles[:self.max_codefiles]

        self.set_specific_configs()
        return

    def update_codefiles_in_gui(self):
        """
        Update GUI for a new set of codefiles (change of directory or
        general.config['codefiles']).
        """
        # Special case: no codefiles
        if self.codefiles is None:
            for i in range(self.max_codefiles):
                self.cf_radio_dict[i].config(state=tk.DISABLED)
            self.specific_configs = None
            self.fullname = self.filename = self.version = self.timestamp = \
                self.student_name = self.email = None
            self.menu_setup.entryconfig(self.setup_specific_loc,
                                        label='Setup codefile...',
                                        state=tk.DISABLED)
            return

        # Set codefile radio buttons for new codefiles
        cf_n = len(self.codefiles)
        for i in range(self.max_codefiles):
            if i < cf_n:
                self.cf_text_dict[i].set(self.codefiles[i])
                self.cf_radio_dict[i].config(state=tk.NORMAL)
            else:
                self.cf_text_dict[i].set('')
                self.cf_radio_dict[i].config(state=tk.DISABLED)
        self.codefile_index = 0
        self.codefile = self.codefiles[self.codefile_index]
        self.cf_index.set(self.codefile_index)
        self.cf_radio_dict[self.codefile_index].select()

        # Set configuration menu for new codefiles
        self.menu_setup.entryconfig(self.setup_specific_loc,
                                    label="Setup " +
                                    self.codefiles[0] + "...",
                                    state=tk.NORMAL)
        return

    def choose_student_file(self, *args):
        """
        Respond to user choosing a new student file
        """
        self.update_selected_student()
        return

    def choose_codefile(self, *args):
        if self.active_letter_file is not None:
            self.write_text(self.letter.get("1.0", "end-1c"),
                            self.active_letter_file)

        self.codefile_index = self.cf_index.get()
        self.codefile = self.codefiles[self.codefile_index]
        self.menu_setup.entryconfig(self.setup_specific_loc,
                                    label="Setup " + self.codefile +
                                          "...",
                                    state=tk.NORMAL)
        self.get_student_files(forceFirst=False)
        if self.student_menu_built:
            self.update_gui(new_codefiles=False, new_codefile_files=True)
        return

    def update_codefile_files_in_gui(self):
        """
        Update GUI for a new selected codefile, and therefore a new set of
        corresponding student files.
        """
        if self.codefiles is None:
            self.dropdownMenu["menu"].delete(0, "end")
            self.chosen_file.set('')
            self.dropdownMenu.config(state=tk.DISABLED)
            self.file_count.config(text="File count: 0")
            self.current_code = '(no code)'
            self.input.configure(state="normal")
            self.input.delete(1.0, tk.END)
            self.input.insert(tk.END, self.current_code)
            self.input.configure(state="disabled")
            return

        if self.file_label is None or len(self.student_name) == 0:
            self.dropdownMenu.config(state=tk.DISABLED)
            self.file_count.config(text="File count: 0")
            self.chosen_file.set('')
            self.current_code = '(no code)'
            self.input.configure(state="normal")
            self.input.delete(1.0, tk.END)
            self.input.insert(tk.END, self.current_code)
            self.input.configure(state="disabled")

        else:
            menu = self.dropdownMenu["menu"]
            menu.delete(0, "end")
            for string in self.file_label:
                menu.add_command(label=string,
                                 command=lambda value=string:
                                     self.chosen_file.set(value))

            self.chosen_file.set(self.file_label[0])
            self.dropdownMenu.config(state=tk.NORMAL)
            self.file_count.config(text="File count: " +
                                   str(len(self.file_label)))

        self.update_selected_student()
        return

    def update_selected_student(self):
        import os.path
        if self.active_letter_file is not None:
            self.write_text(self.letter.get("1.0", "end-1c"),
                            self.active_letter_file)
        who = self.chosen_file.get()
        if who == '' or self.codefiles is None or self.file_label is None or \
                len(self.student_name) == 0:
            self.current_code = '(no code)'
            self.input.configure(state="normal")
            self.input.delete(1.0, tk.END)
            self.input.insert(tk.END, self.current_code)
            self.input.configure(state="disabled")
            self.input_analysis.configure(state="normal")
            self.input_analysis.delete(1.0, tk.END)
            self.input_analysis.insert(tk.END, "(no analysis)")
            self.input_analysis.configure(state="disabled")
            self.messages.configure(state='normal')
            self.messages.delete(1.0, tk.END)
            self.messages.insert(tk.END, "(no messages)")
            self.messages.configure(state='disabled')
            self.output.configure(state="normal")
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, "(no output)")
            self.output.configure(state="disabled")
            self.output_analysis.configure(state="normal")
            self.output_analysis.delete(1.0, tk.END)
            self.output_analysis.insert(tk.END, "(no analysis)")
            self.output_analysis.configure(state="disabled")
            self.letter.delete(1.0, tk.END)
            self.letter.insert(tk.END, "(no analysis)")
            self.active_letter_file = None
            return

        student_index = self.file_label.index(who)
        sandbox = self.get_dir_name(student_index)
        fname = os.path.join(sandbox, self.versioned_filename[student_index])
        self.current_code = self.get_text_and_put_in_tab(
            self.fullname[student_index], self.input, "(no input)",
            disabled=True)
        self.get_text_and_put_in_tab(fname + "pre", self.input_analysis,
                                     "(no analysis)", disabled=True)
        self.get_text_and_put_in_tab(fname + "msg", self.messages,
                                     "(no messages)", disabled=True)
        self.get_text_and_put_in_tab(fname + "out", self.output,
                                     "(no output)", disabled=True)
        self.get_text_and_put_in_tab(fname + "pst", self.output_analysis,
                                     "(no analysis)", disabled=True)
        self.active_letter_file = fname + "ltr"
        self.get_text_and_put_in_tab(self.active_letter_file, self.letter,
                                     "(no letter)", disabled=False)
        return

    def update_gui(self, new_codefiles, new_codefile_files):
        if new_codefiles:
            self.update_codefiles_in_gui()
        if new_codefile_files:
            self.update_codefile_files_in_gui()

    def get_codefiles(self):
        """
        Verify and make a list of codefiles based on comments in
        one_time_setup().  An example is "Prob1.R, Prob2.Rmd".
        Currently, items must end in .R, .Rmd, .RRmd, .sas or .py.
        If a star is on the left, e.g., "*.R", only that single item is
        allowed (currently).
        Any star designation is expanded to all matching codefiles (but only
        those matching self.general.config(['file.format']) or of a "%s_%f"
        format).  These specific files are then stored in the local
        general configuration file.
        Stores list or None in self.codefiles.
        """
        import re
        import os
        import time
        file_list = self.general_config['codefiles'].split(",")
        file_list = [f.strip() for f in file_list]
        ok_re = re.compile(".+[.](R|Rmd|RRmd|sas|py)$", re.IGNORECASE)
        files_ok = [ok_re.search(s) is not None for s in file_list]
        star_cnt = sum(["*" in f for f in file_list])
        bad_stars = star_cnt > 1 or (star_cnt == 1 and len(files_ok) > 1)
        if not all(files_ok) or bad_stars:
            messagebox.showwarning("Bad 'codefiles'",
                                   "'codefiles' is in the wrong format")
            self.codefiles = None
            self.current_code = None
            return
        if star_cnt == 0:
            self.codefiles = file_list
            return

        # Expand *.(R|Rmd|RRmd)" to all files (modulo student name, etc.)
        # according to the general configuration 'file_format'.
        star_ext = file_list[0][2:]
        isOKext_re = re.compile(".+[.](R|Rmd|sas|py)$", re.IGNORECASE) if \
            star_ext == "RRmd" else \
            re.compile(".+[.]" + star_ext + "$", re.IGNORECASE)
        all_files = os.listdir()
        OK_files = [isOKext_re.search(f) for f in all_files]
        OK_files = [x.group(0) for x in OK_files if x is not None]
        all_matches = [self.parse_one_filename(f)['filename']
                       for f in OK_files]
        all_matches = [re.sub("[.]r", ".R", x) for x in all_matches]
        nbad = len([x for x in all_matches if len(x) == 0])
        if nbad > 0:
            messagebox.showwarning("Bad file formats", "Ignored " + str(nbad) +
                                   " files not conforming to file format: " +
                                   self.general_config['file_format'])
        file_list = [x for x in set(all_matches) if len(x) > 0]
        if len(file_list) == 0:
            self.codefiles = None
            return
        self.general_config['codefiles'] = ", ".join(file_list)
        self.general_config['config_mod_time'] = time.time()
        self.write_config_file(self.general_config_fname,
                               self.general_config)

        self.codefiles = file_list
        return

    def parse_one_filename(self, name):
        """
        Convert a filename into a dictionary with elements 'filename' (with
        extension, but dropping any -# version suffix), 'version', 'timestamp',
        'student_name', and 'email' according to the value of the general
        configuration's 'file_format' and the corresponding % notation
        documented in one_time_setup().
        Requires prior call to set_file_format_info() to set
        'self.filename_separator', 'self.file_format_items',
        'self.late_index_in_file_format', and
        'self.student_name_in_file_format'.
        Argument:
        'name': (str) a "segemented" file name according to 'file_format'
                specifed by the user in the general configuration.
        """
        import re
        re_dotExt = re.compile("(.+)([.][a-zA-Z]+$)")
        re_version = re.compile("(.+)(-[0-9]{1,2}$)")

        fmt_n = len(self.file_format_items)
        parts = name.split(self.filename_separator)
        name_n = len(parts)
        file_format_items = self.file_format_items

        rtn = {'filename': '', 'version': 0, 'timestamp': '',
               'student_name': '', 'email': '', 'late': False}

        # Handle optional "late" field
        late_dropped = False
        if self.late_index_in_file_format >= 0 and \
                self.late_index_in_file_format < name_n:
            if parts[self.late_index_in_file_format].upper() == "LATE":
                parts.remove(parts[self.late_index_in_file_format])
                name_n -= 1
                rtn['late'] = True
                late_dropped = True

        if (name_n > fmt_n) or (name_n < fmt_n and name_n != 2):
            return rtn

        # Extract information from fields
        short = True if name_n < fmt_n and not late_dropped else False
        for element in range(name_n):
            field = ["%s", "%f"][element] if short else \
                    file_format_items[element]
            value = parts[element]
            if field == "%j":
                continue
            elif field == "%t":
                rtn['timestamp'] = value
            elif field == "%s":
                rtn['student_name'] = value
            elif field == "%e":
                rtn['email'] = value
            else:  # field == "%f": extract version and base filename
                dot_srch = re_dotExt.search(value)
                if dot_srch is None:
                    messagebox.showwarning("No extention",
                                           name + " has no extention")
                    self.on_quit()
                ext = dot_srch.group(2)
                fname = dot_srch.group(1)
                vers_srch = re_version.search(fname)
                if vers_srch is None:
                    rtn['filename'] = value
                else:
                    rtn['filename'] = vers_srch.group(1) + ext
                    rtn['version'] = int(vers_srch.group(2)[1:])
        return rtn

    def parse_codefile_names(self, names):
        """ Convert all files like ".*_foo.ext" into a list of lists matching
            the % notation documented in one_time_setup().
            Only keep the latest version of versioned (foo-#.ext) files.
        """
        self.fullname = []
        self.filename = []
        self.version = []
        self.versioned_filename = []
        self.timestamp = []
        self.student_name = []
        self.email = []
        self.file_label = []
        if names is None:
            return

        # Process each filename
        for index in range(len(names)):
            fname = names[index]
            elements = self.parse_one_filename(fname)
            if len(elements['filename']) == 0:
                continue
            sname = elements['student_name'].lower()
            email = elements['email'].lower()
            filename = elements['filename']
            # add in email if needed and possible
            if elements['student_name'] != '' and \
                    elements['email'] == '' and \
                    self.roster_email is not None and \
                    self.roster_fullname is not None:
                cnt = self.roster_fullname.count(sname)
                if cnt > 0:
                    loc = self.roster_fullname.index(sname)
                    elements['email'] = self.roster_email[loc]
                    email = elements['email']
            # add in student if needed and possible
            if elements['email'] != '' and \
                    elements['student_name'] == '' and \
                    self.roster_fullname is not None and \
                    self.roster_email is not None:
                cnt = self.roster_email.count(email)
                if cnt > 0:
                    loc = self.roster_email.index(email)
                    elements['student_name'] = self.roster_fullname[loc]
                    sname = elements['student_name']
            # Set file label (for "dropdown" list of files)
            if self.student_name_in_file_format or elements['email'] == '':
                file_label = elements['student_name']
                if elements['version'] > 0:
                    file_label = file_label + " (" + \
                                 str(elements['version']) + ")"
            else:
                file_label = elements['email']
                if elements['version'] > 0:
                    file_label = file_label + " (" + \
                                 str(elements['version']) + ")"

            # Check if this is a different version of a file already
            # in the list
            if sname != '':
                cnt = self.student_name.count(sname)
                if cnt == 0:
                    loc = -1
                else:
                    loc = self.student_name.index(sname)
            else:
                cnt = self.email.count(email)
                if cnt == 0:
                    loc = -1
                else:
                    loc = self.email.index(email)

            # Make versioned filenam
            if elements['version'] == 0:
                vfn = filename
            else:
                ext = self.get_extension(filename)
                vfn = filename[:len(filename)-len(ext)] + "-" + \
                    str(elements['version']) + ext
            if loc == -1:
                self.fullname.append(fname)
                self.filename.append(elements['filename'])
                self.version.append(elements['version'])
                self.versioned_filename.append(vfn)
                self.timestamp.append(elements['timestamp'])
                self.student_name.append(elements['student_name'])
                self.email.append(elements['email'])
                self.file_label.append(file_label)
            elif self.version[loc] < elements['version']:
                self.fullname[loc] = fname
                self.filename[loc] = elements['filename']
                self.version[loc] = elements['version']
                self.versioned_filename[loc] = vfn
                self.timestamp[loc] = elements['timestamp']
                self.student_name[loc] = elements['student_name']
                self.email[loc] = elements['email']
                self.file_label[loc] = file_label
        return

    def get_student_files(self, forceFirst):
        """
        Read self.dir and construct list of .ext files for the currently
        selected element of self.codefiles.
        Main effect is to use parse_codefile_names to fill in self.fullname,
        self.email, self.student_name, etc.
        """
        import os
        import re
        if self.codefiles is None:
            self.parse_codefile_names(None)
            return
        if forceFirst:  # or self.cf_index is None:
            index = 0
        else:
            index = self.codefile_index  # self.cf_index.get()
        rtn = []
        parts = self.codefiles[index].split(".")
        if len(parts) > 2:
            parts = (".".join(parts[:-1]), parts[-1])
        codefile_re = re.compile(self.filename_separator + parts[0] +
                                 "(-[0-9]{1,2})?" + "." + parts[1] + "$",
                                 re.IGNORECASE)
        for file in os.listdir(self.dir):
            if codefile_re.search(file) is not None:
                rtn.append(file)
        self.parse_codefile_names(rtn)
        return

    def on_quit(self):
        if self.active_letter_file is not None:
            self.write_text(self.letter.get("1.0", "end-1c"),
                            self.active_letter_file)
        self.master.destroy()
        self.quit()

    def choose_directory(self):
        """ Run directory select dialog """
        # d = ttk.chooseDirectory(master=self, command=self.new_dir)  #T#
        # d.popup()
        dir = filedialog.askdirectory(initialdir=self.dir,
                                      title="AutoGrader    Choose a directory")
        if dir != '':
            self.new_dir(dir)
        return

    def new_dir(self, dir):
        from os import chdir
        self.dir = dir
        self.root.title('R Grader: ' + dir)
        chdir(dir)
        self.setup_for_new_dir()
        self.update_gui(new_codefiles=True, new_codefile_files=True)
        return

    def f_path(self, fname, add_dir=False):
        """ Construct file path based on self.dir and self.file.common_len """
        from os.path import join
        in_type = 'list'
        if type(fname) is not list:
            in_type = 'not list'
            fname = [fname]
        if add_dir:
            fname = [join(self.dir, f) for f in fname]
        if in_type == 'not list':
            fname = fname[0]
        return fname

    def get_extension(self, fname):
        """ Return extension, including ".". """
        period = fname.rfind(".")
        if period == -1:
            return None
        return fname[period:]

    def run_all(self, who=None):
        import os
        import os.path
        if len(self.file_label) != 0 and self.file_label[0] != '':
            config = self.specific_configs[self.codefile + ".config"]
            config_time = config['config_mod_time']
            for who in self.file_label:
                student_index = self.file_label.index(who)
                input_mod_time = os.path.getmtime(self.fullname[student_index])
                sandbox = self.get_dir_name(student_index)
                outname = self.versioned_filename[student_index] + "out"
                outfile = os.path.join(sandbox, outname)
                if os.access(outfile, os.R_OK):
                    last_run_time = os.path.getmtime(outfile)
                else:
                    last_run_time = -1.0
                if last_run_time < input_mod_time or \
                        last_run_time < config_time:
                    self.run_one(who)
        return

    def run_one(self, who=None):
        import os
        import os.path
        if who is None:
            who = self.chosen_file.get()
        c = self.file_label.count(who)
        if c != 1:
            messagebox.showwarning("Programmer error", "run_one error")
            return
        student_index = self.file_label.index(who)
        if who == self.chosen_file.get():
            current_code = self.current_code + "\n"
        else:
            current_code = self.get_text(self.fullname[student_index]) + "\n"

        # create sandbox if needed
        sandbox = self.get_dir_name(student_index)
        if not os.path.isdir(sandbox):
            try:
                os.mkdir(sandbox)
            except OSError:
                messagebox.showwarning("Cannot create sandbox",
                                       "Failed to create " + sandbox)
                return

        # Setup blank letter
        codefile = self.versioned_filename[student_index]
        self.active_letter_file = os.path.join(sandbox, codefile + "ltr")
        if who == self.chosen_file.get():
            self.letter.delete(1.0, tk.END)
        self.write_text('(no letter)', self.active_letter_file)
        config = self.specific_configs[self.codefile + ".config"]
        total_points = config['total_points']
        if total_points <= 0:
            total_points = None

        # Pre-analysis
        (pre_analysis_points, pre_analysis_points_text) = \
            self.pre_analyze(current_code, sandbox, student_index)

        # Analysis
        self.submit_code(current_code, sandbox, student_index)

        # Post-analysis
        (post_analysis_points, post_analysis_points_text) = \
            self.post_analyze(sandbox, student_index)

        # Write letter
        self.write_letter(codefile, total_points,
                          pre_analysis_points, pre_analysis_points_text,
                          post_analysis_points, post_analysis_points_text)

        return

    def pull_off_points(self, line):
        """ Given text optionally preceeded by "{myPoints}", return
            myPoints and the cleaned text. """
        temp = self.re_points.search(line)
        if temp is None:
            points = None
        else:
            line = temp.group(2)
            try:
                points = float(temp.group(1))
            except ValueError:
                messagebox.showwarning("Bad points: " + line)
                points = None
        return (points, line)

    def pre_analyze(self, text, sandbox, index):
        """ Analyze submitted code before running it """
        import re
        import os.path
        codefile = self.codefile
        ext = self.get_extension(codefile).upper()
        config = self.specific_configs[codefile + ".config"]
        result = ''
        points_text = ''
        points_docked = 0.0
        textx = text.split("\n")

        # Define comments for current programming language
        if ext in ('.R', '.RMD', '.PY'):
            re_comment = re.compile("^\\s*#")
        elif ext == '.SAS':
            re_comment = re.compile("^\\s*[/][*]")
        else:
            messagebox.showwarning("Programmer error", "in pre_analyze")
        comment_count = sum([re_comment.search(s) is not None for s in textx])
        result += "Desired / actual comments = " + \
                  str(config['min_comments']) + " / " + \
                  str(comment_count) + "\n"

        re_blank = re.compile("^\\s*$")
        blank_count = sum([re_blank.match(s) is not None for s in textx])
        result += "Desired / actual blanks = " + str(config['min_blanks']) + \
                  " / " + str(blank_count) + "\n\n"

        # Handle required and prohibited text
        (pts, temp) = self.req_and_prohib(config, text, "code")
        result += temp
        points_text += temp
        if pts is not None:
            points_docked += pts

        # Save and display pre-analysis
        pre = os.path.join(sandbox, self.versioned_filename[index] + "pre")
        self.write_text(result, pre)
        if self.file_label[index] == self.chosen_file.get():
            self.input_analysis.configure(state="normal")
            self.input_analysis.delete(1.0, tk.END)
            self.input_analysis.insert(tk.END, result)
            self.input_analysis.configure(state="disabled")

        return (points_docked, points_text)

    def multi_drop(self, lst, todrop):
        """ remove elements 'todrop' from list 'list' """
        for i in sorted(todrop, reverse=True):
            del lst[i]
        return lst

    def post_analyze(self, sandbox, index):
        import os.path
        codefile = self.versioned_filename[index]
        ext = self.get_extension(codefile).upper()
        outfile = os.path.join(sandbox, codefile + "out")
        text = self.get_text_and_put_in_tab(outfile, self.output,
                                            "(no output)", disabled=True,
                                            SAS=(ext == ".SAS"))
        if text is None:
            self.write_text("No output, so no messages",
                            os.path.join(sandbox, codefile + "msg"))
            self.write_text("No output, so no output analysis",
                            os.path.join(sandbox, codefile + "pst"))
            fail_text = "Analysis of " + codefile + " awards " + \
                        "zero points because no output was produced."
            self.write_text(fail_text, self.active_letter_file)
            self.letter.delete(1.0, tk.END)
            self.letter.insert(tk.END, fail_text)
            return (0, '')

        config = self.specific_configs[self.codefile + ".config"]
        file_label = self.file_label[index]
        if ext in ('.R', '.RMD'):
            (post_analysis_points_docked, post_analysis_points_text) = \
                self.R_post_analyze(sandbox, codefile, outfile, text, config,
                                    file_label)
        elif ext in ('.SAS'):
            (post_analysis_points_docked, post_analysis_points_text) = \
                self.SAS_post_analyze(sandbox, codefile, outfile, text, config,
                                      file_label)
        elif ext in ('.PY'):
            (post_analysis_points_docked, post_analysis_points_text) = \
                self.PY_post_analyze(sandbox, codefile, outfile, text, config,
                                     file_label)
        else:
            messagebox.showwarning("Missing feature", "post for " + ext)
            (post_analysis_points_docked, post_analysis_points_text) = (0, '')

        return (post_analysis_points_docked, post_analysis_points_text)

    def R_post_analyze(self, sandbox, codefile, outfile, text, config,
                       file_label):
        """ Analyze results from submitting R code """
        import re
        import os.path

        textx = text.split("\n")
        out_analysis = ''
        messages = ''
        points_text = ''
        points_docked = 0.0
        # letter = 'You did a pretty good job.'
        re_warning = re.compile("^Warning message:")
        re_error = re.compile("^(Error in|Error:)")

        # Look for error messages
        error_line_nums = [num for (num, txt) in enumerate(textx) if
                           re_error.search(txt) is not None]
        error_count = len(error_line_nums)
        if error_count == 0:
            error_lines = None
        else:
            error_lines = ["@ " + str(i) + " " + textx[i] + "\n" + textx[i+1]
                           for i in error_line_nums]
            # Remove benign "package built" errors
            ignore_re = re.compile("package .* was built under R version")
            ignore_nums = [num for (num, txt) in enumerate(error_lines)
                           if ignore_re.search(txt) is not None]
            error_lines = self.multi_drop(error_lines, ignore_nums)
            error_count = len(error_lines)
            if len(error_lines) == 0:
                error_lines = None
        # Prepare to add errors to "messages" tab
        if error_count > 0:
            messages += "**** ERRORS ****\n"
            for line in error_lines:
                messages += line + "\n"
        temp = "Allowed / actual errors = " + \
               str(config['max_errors']) + " / " + \
               str(error_count) + "\n"
        out_analysis += temp
        points_text += temp

        # Look for warning messages
        warning_line_nums = [num for (num, txt) in enumerate(textx) if
                             re_warning.search(txt) is not None]
        warning_count = len(warning_line_nums)
        if warning_count == 0:
            warning_lines = None
        else:
            # Warning lines may span multiple lines (allow up to 4)
            len_t = len(textx)
            warning_lines = []
            for i in warning_line_nums:
                temp = "@ " + str(i) + " "
                if len_t > i + 1 and len(textx[i+1]) > 0 and \
                        textx[i+1][0] != ">":
                    temp += textx[i+1] + "\n"
                    if len_t > i + 2 and len(textx[i+2]) > 0 and \
                            textx[i+2][0] != ">":
                        temp += textx[i+2] + "\n"
                        if len_t > i + 3 and len(textx[i+3]) > 0 and \
                                textx[i+3][0] != ">":
                            temp += textx[i+3] + "\n"
                warning_lines.append(temp)
            ignore_re = re.compile("package .* was built under R version")
            ignore_nums = [num for (num, txt) in enumerate(warning_lines)
                           if ignore_re.search(txt) is not None]
            warning_lines = self.multi_drop(warning_lines, ignore_nums)
            warning_count = len(warning_lines)
            if len(warning_lines) == 0:
                warning_lines = None
        if warning_count > 0:
            if error_count > 0:
                messages += "\n"
            messages += "**** WARNINGS ****\n"
            for line in warning_lines:
                messages += line + "\n"
        temp = "Allowed / actual warnings = " + \
               str(config['max_warnings']) + " / " + \
               str(warning_count) + "\n"
        out_analysis += temp
        points_text += temp

        (pts, temp) = self.req_and_prohib(config, text, "output")
        out_analysis += temp
        points_text += temp
        if pts is not None:
            points_docked += pts

        # Save and display messages and post-analysis
        if messages == '':
            messages = '(no warnings or errors)'
        if out_analysis == '':
            out_analysis = '(no output problems)'
        msg = os.path.join(sandbox, codefile + "msg")
        self.write_text(messages, msg)
        pst = os.path.join(sandbox, codefile + "pst")
        self.write_text(out_analysis, pst)
        # self.write_text(letter, self.active_letter_file)
        if file_label == self.chosen_file.get():
            self.messages.configure(state='normal')
            self.messages.delete(1.0, tk.END)
            self.messages.insert(tk.END, messages)
            self.messages.configure(state='disabled')
            self.output_analysis.configure(state="normal")
            self.output_analysis.delete(1.0, tk.END)
            self.output_analysis.insert(tk.END, out_analysis)
            self.output_analysis.configure(state="disabled")
            # self.letter.delete(1.0, tk.END)
            # self.letter.insert(tk.END, letter)
        return (points_docked, points_text)

    def SAS_post_analyze(self, sandbox, codefile, outfile, text, config,
                         file_label):
        """ Analyze results from submitting SAS code """
        import re
        import os.path

        # textx = text.split("\n")
        log = self.get_text(os.path.join(sandbox, codefile + "log"))
        logx = log.split("\n")
        out_analysis = ''
        messages = ''
        points_docked = 0.0
        points_text = ''
        # letter = 'You did a pretty good job.'
        re_warning = re.compile("^WARNING:")
        re_error = re.compile("^ERROR:")

        # Look for error messages
        error_line_nums = [num for (num, txt) in enumerate(logx) if
                           re_error.search(txt) is not None]
        error_count = len(error_line_nums)
        if error_count == 0:
            error_lines = None
        else:
            len_t = len(logx)
            error_lines = []
            for i in error_line_nums:
                temp = "@ " + str(i) + " " + logx[i] + "\n"
                if len_t > i + 1 and len(logx[i+1]) > 0 and \
                        logx[i+1][0] not in "0123456789":
                    temp += logx[i+1] + "\n"
                    if len_t > i + 2 and len(logx[i+2]) > 0 and \
                            logx[i+2][0] not in "0123456789":
                        temp += logx[i+2] + "\n"
                        if len_t > i + 3 and len(logx[i+3]) > 0 and \
                                logx[i+3][0] not in "0123456789":
                            temp += logx[i+3] + "\n"
                error_lines.append(temp)
            ignore_re = re.compile("Errors printed on page")
            ignore_nums = [num for (num, txt) in enumerate(error_lines)
                           if ignore_re.search(txt) is not None]
            error_lines = self.multi_drop(error_lines, ignore_nums)
            error_count = len(error_lines)
            if len(error_lines) == 0:
                error_lines = None
        if error_count > 0:
            messages += "**** ERRORS ****\n"
            for line in error_lines:
                messages += line + "\n"
        temp = "Allowed / actual errors = " + \
               str(config['max_errors']) + " / " + \
               str(error_count) + "\n"
        out_analysis += temp
        points_text += temp

        # Look for warning messages
        warning_line_nums = [num for (num, txt) in enumerate(logx) if
                             re_warning.search(txt) is not None]
        warning_count = len(warning_line_nums)
        if warning_count == 0:
            warning_lines = None
        else:
            len_t = len(logx)
            warning_lines = []
            for i in warning_line_nums:
                temp = "@ " + str(i) + " "
                if len_t > i + 1 and len(logx[i+1]) > 0 and \
                        logx[i+1][0] != ">":
                    temp += logx[i+1] + "\n"
                    if len_t > i + 2 and len(logx[i+2]) > 0 and \
                            logx[i+2][0] != ">":
                        temp += logx[i+2] + "\n"
                        if len_t > i + 3 and len(logx[i+3]) > 0 and \
                                logx[i+3][0] != ">":
                            temp += logx[i+3] + "\n"
                warning_lines.append(temp)
            # extend ignore to 'dropped_messages' (4/24/2018)
            ignore_text = "registry customizations"
            dropped_messages = config['dropped_messages'].strip()
            if len(dropped_messages) > 0:
                ignore_text = "|".join([ignore_text] +
                                       dropped_messages.split('\n'))
            ignore_re = re.compile(ignore_text)
            ignore_nums = [num for (num, txt) in enumerate(warning_lines)
                           if ignore_re.search(txt) is not None]
            warning_lines = self.multi_drop(warning_lines, ignore_nums)
            warning_count = len(warning_lines)
            if len(warning_lines) == 0:
                warning_lines = None
        if warning_count > 0:
            if error_count > 0:
                messages += "\n"
            messages += "**** WARNINGS ****\n"
            for line in warning_lines:
                messages += line + "\n"
        temp = "Allowed / actual warnings = " + \
               str(config['max_warnings']) + " / " + \
               str(warning_count) + "\n"
        out_analysis += temp
        points_text += temp

        # Check for required and prohibited output
        (pts, temp) = self.req_and_prohib(config, text, "output")
        out_analysis += temp
        if pts is not None:
            points_docked += pts

        # Save and display messages and post-analysis
        if messages == '':
            messages = '(no warnings or errors)'
        else:
            messages += "\n********************************************\n"
            messages += log
        if out_analysis == '':
            out_analysis = '(no output problems)'
        msg = os.path.join(sandbox, codefile + "msg")
        self.write_text(messages, msg)
        pst = os.path.join(sandbox, codefile + "pst")
        self.write_text(out_analysis, pst)
        # self.write_text(letter, self.active_letter_file)
        if file_label == self.chosen_file.get():
            self.messages.configure(state='normal')
            self.messages.delete(1.0, tk.END)
            self.messages.insert(tk.END, messages)
            self.messages.configure(state='disabled')
            self.output_analysis.configure(state='normal')
            self.output_analysis.delete(1.0, tk.END)
            self.output_analysis.insert(tk.END, out_analysis)
            self.output_analysis.configure(state='disabled')
            # self.letter.delete(1.0, tk.END)
            # self.letter.insert(tk.END, letter)
        return (points_docked, points_text)

    def PY_post_analyze(self, sandbox, codefile, outfile, text, config,
                        file_label):
        """ Analyze results from submitting python code """
        # import re
        import os.path

        # textx = text.split("\n")
        out_analysis = ''
        messages = ''
        points_text = ''
        points_docked = 0.0

        # Put errors to "messages" tab
        error_file = os.path.join(sandbox, codefile + 'err')
        messages = self.get_text(error_file)

        # Check for required and prohibited output
        (pts, temp) = self.req_and_prohib(config, text, "output")
        out_analysis += temp
        if pts is not None:
            points_docked += pts

        # Save and display messages and post-analysis
        if messages == '':
            messages = '(no warnings or errors)'
        if out_analysis == '':
            out_analysis = '(no output problems)'
        msg = os.path.join(sandbox, codefile + "msg")
        self.write_text(messages, msg)
        pst = os.path.join(sandbox, codefile + "pst")
        self.write_text(out_analysis, pst)
        # self.write_text(letter, self.active_letter_file)
        if file_label == self.chosen_file.get():
            self.messages.configure(state='normal')
            self.messages.delete(1.0, tk.END)
            self.messages.insert(tk.END, messages)
            self.messages.configure(state='disabled')
            self.output_analysis.configure(state="normal")
            self.output_analysis.delete(1.0, tk.END)
            self.output_analysis.insert(tk.END, out_analysis)
            self.output_analysis.configure(state="disabled")
            # self.letter.delete(1.0, tk.END)
            # self.letter.insert(tk.END, letter)
        return (points_docked, points_text)

    def req_and_prohib(self, config, text, code_or_output):
        """ Write output concerning required and prohibited text """
        # Check for required output
        import re
        # Change '\r\n' to '\n' to facilate using search for '\n', because
        # '^' and '$' will not work on this multiline single text string.
        text = re.sub('\r\n', '\n', text)
        out_analysis = ''
        points_docked = 0.0
        item = 'req_' + code_or_output
        req_output = config[item].split('\n')
        req_output = [r.strip() for r in req_output]
        for line in req_output:
            if len(line) == 0:
                continue
            (points, line) = self.pull_off_points(line)
            # Do the match (exact if quoted; otherwise a regular expression)
            if line[0] == line[-1] and line[0] in "\"'":
                if len(line) < 3:
                    continue
                ok = line[1:-2] in text
            else:
                try:
                    req_re = re.compile(line)
                except re.error:
                    messagebox.showwarning("Cannot create regular expression",
                                           line + "is invalid")
                    return (-9999, "Bad Regular expression")
                ok = req_re.search(text)
            if not ok:
                if points is None:
                    out_analysis += "Missing output: " + line + "\n"
                else:
                    if points < 0.0:
                        adj = "missing"
                    else:
                        adj = "avoided"
                    out_analysis += str(points) + " points for " + adj + \
                        " " + code_or_output + ": " + line + "\n"
                    points_docked += points

        # Check for prohibited output
        item = 'prohib_' + code_or_output
        prohib_output = config[item].split('\n')
        prohib_output = [p.strip() for p in prohib_output]
        for line in prohib_output:
            if len(line) == 0:
                continue
            (points, line) = self.pull_off_points(line)
            # Do the match (exact if quoted; otherwise a regular expression)
            if line[0] == line[-1] and line[0] in "\"'":
                if len(line) < 3:
                    continue
                bad = line[1:-2] in text
            else:
                prohib_re = re.compile(line)
                bad = prohib_re.search(text)
            if bad:
                if points is None:
                    out_analysis += "Prohibited output: " + line + "\n"
                else:
                    if points < 0.0:
                        adj1 = ""
                        adj2 = " prohibited"
                    else:
                        adj1 = " extra credit"
                        adj2 = ""
                    out_analysis += str(points) + adj1 + " points for" + \
                        adj2 + " output: " + line + "\n"
                    points_docked += points

        return (points_docked, out_analysis)

    def write_letter(self, codefile, total_points,
                     pre_analysis_points, pre_analysis_text,
                     post_analysis_points, post_analysis_text):
        letter = "Analysis of homework file: " + codefile + "\n\n"
        if total_points is not None and pre_analysis_points is not None and \
                post_analysis_points is not None:
            points_earned = total_points + pre_analysis_points + \
                            post_analysis_points
            letter += "You scored " + str(points_earned) + \
                      " out of " + str(total_points) + ".\n\n"
        if pre_analysis_text is not None:
            letter += "\nCode analysis:\n" + pre_analysis_text
        if post_analysis_text is not None:
            letter += "\nAnalysis of results:\n" + post_analysis_text
        self.write_text(letter, self.active_letter_file)
        self.letter.delete(1.0, tk.END)
        self.letter.insert(tk.END, letter)
        return

    def submit_code(self, code, sandbox, index):
        """
        Batch submit code from one file in a sandbox.

        .R mechanism is "R CMD BATCH [options] infile [outfile]".
        Important note: on Windows, new libraries are probably installed in
        something like C:\\Users\\myUserName\\Documents\\R\\win-library\\3.4.
        To allow access to these libraries, set a system environmenal variable
        (Control Panel / System / Advanced / Environment) called R_LIBS_USER
        to that location, but with the final "#.#" replaced with "%v".

        For .Rmd files (with "output: html_document"), the R code is:
        library("knitr"); knit("myFile.Rmd")
        library("markdown"); markdown::render("myFile.md")
        to create myFile.html.
        """
        import os.path
        import os
        import shutil
        import subprocess
        codefile = self.codefile
        ext = self.get_extension(codefile).upper()

        # copy auxiliary files to sandbox
        config = self.specific_configs[self.codefile + ".config"]
        aux_files = config['aux_files'].split("\n")
        for aux in aux_files:
            aux = aux.strip()
            if aux == '':
                continue
            slashes = aux.count("/")
            if slashes > 1:
                messagebox.showwarning("Missing feature",
                                       "Aux. file " + aux +
                                       " is nested too deep")
                continue
            if slashes == 1:
                directory = os.path.join(sandbox, aux.split("/")[0])
                if not os.path.isdir(directory):
                    try:
                        os.mkdir(directory)
                    except OSError:
                        messagebox.showwarning("Cannot create directory",
                                               "Failed to create " +
                                               directory)
                        continue
            if not os.access(aux, os.R_OK):
                messagebox.showwarning("Missing file",
                                       "Aux. file " + aux + " is missing")
                continue
            aname_out = os.path.join(sandbox, aux)
            if not os.access(aname_out, os.R_OK):
                try:
                    shutil.copy(aux, aname_out)
                except OSError:
                    messagebox.showwarning("Cannot copy aux. file",
                                           "Failed to write " + aname_out)

        # setup runstring
        if ext == ".R":
            (runstring, output_name) = self.setup_R_runstring(code, sandbox,
                                                              index)
        elif ext == ".RMD":
            (runstring, output_name) = self.setup_RMD_runstring(code, sandbox,
                                                                index)
        elif ext == ".SAS":
            (runstring, output_name) = self.setup_SAS_runstring(code, sandbox,
                                                                index)
        elif ext == ".PY":
            (runstring, output_name) = self.setup_python_runstring(code,
                                                                   sandbox,
                                                                   index)
        else:
            print("not coded yet")
            return

        # Run the code in the sandbox
        # https://stackoverflow.com/questions/4760215/running-shell-command-
        #         from-python-and-capturing-the-output
        os.chdir(sandbox)
        if type(runstring) is str:
            code = subprocess.run(runstring, shell=True)
        else:
            codes = []
            for rs in runstring:
                codes.append(subprocess.run(rs, shell=True))
            code = codes[-1]
        os.chdir(self.dir)

        # Analyze output
        code_output = self.get_text(output_name)
        err_msg = "[Error code is " + str(code.returncode) + "]"
        if code_output is None:
            code_output = err_msg
        else:
            code_output = err_msg + "\n\n" + code_output

        # Save and display output
        self.write_text(code_output, output_name)
        self.output.configure(state='normal')
        self.output.delete(1.0, tk.END)
        self.output.insert(tk.END, code_output)
        self.output.configure(state='disabled')

        return

    def setup_R_runstring(self, code, sandbox, index):
        """
        Setup R runstring and make needed generic
        modifications to input code file.
        """
        import os.path
        import re
        sand_name = self.versioned_filename[index]
        output_name = os.path.join(sandbox, sand_name + "out")
        # Students tend to put help() or ? in code.
        # We want to remove that.
        code = re.sub("((^|\\n)[:blank:]*)([?])",
                      "\\1### ?", code)
        code = re.sub("((^|\\n)[:blank:]*)help[(]",
                      "\\1### help(", code)

        config = self.specific_configs[self.codefile + ".config"]
        prepend = config["code_prepend"].strip()
        if prepend != "":
            code = prepend + "\n" + code
        append = config["code_append"].strip()
        if append != "":
            code = code + "\n" + append + "\n"

        self.write_text(code,
                        os.path.join(sandbox, sand_name))

        inoutfiles = '"' + sand_name + '"' + ' "' + sand_name + 'out"'
        runstring = 'R CMD BATCH --no-save --no-restore --quiet ' + \
                    inoutfiles
        return (runstring, output_name)

    def setup_RMD_runstring(self, code, sandbox, index):
        import os
        import os.path
        import re
        sand_name = self.versioned_filename[index]
        output_name = os.path.join(sandbox, sand_name + ".out")
        base_name = sand_name[:-4]
        code = re.sub("((^|\\n)[:blank:]*)([?])",
                      "\\1### ?", code)
        code = re.sub("((^|\\n)[:blank:]*)help[(]",
                      "\\1### help(", code)
        code = re.sub("pdf_document",
                      "html_document", code)
        code = re.sub("(w|W)ord_document",
                      "html_document", code)

        config = self.specific_configs[self.codefile + ".config"]
        prepend = config["code_prepend"].strip()
        if prepend != "":
            firstR_re = re.compile("\\n\\s*```\\s*[{]\\s*(r|R)")
            firstR = firstR_re.search(code)
            if firstR is None or firstR.span(0)[0] == 0:
                # Add popup message
                return
            firstR = firstR.span(0)[0]
            code = code[:firstR+2] + "```{r autoGrader Prepend}\n" + \
                prepend + "\n```\n\n" + code[firstR+2:]
        append = config["code_append"].strip()
        if append != "":
            code = code + "\n```{r autoGrader Append}\n" + append + \
                   "\n```\n"

        self.write_text(code,
                        os.path.join(sandbox, sand_name))

        # For .Rmd files (with "output: html_document"), the R code is:
        knit_file_text = 'library("knitr")\n' + \
                         'knit("' + sand_name + '")\n' + \
                         'library("markdown")\n' + \
                         'markdownToHTML("' + base_name + '.md", "' + \
                         sand_name + '.html")'
        knit_filename = sand_name + ".knit.R"
        self.write_text(knit_file_text, os.path.join(sandbox, knit_filename))

        inoutfiles = '"' + knit_filename + '"' + ' "' + sand_name + \
                     'out"'
        runstring = 'R CMD BATCH --no-save --no-restore --quiet ' + \
                    inoutfiles
        cwd = os.getcwd()
        runstring = [runstring, 'start ' +
                     os.path.join(cwd, sandbox, sand_name + '.html')]
        return (runstring, output_name)

    def setup_SAS_runstring(self, code, sandbox, index):
        # http://www2.sas.com/proceedings/forum2008/017-2008.pdf
        import os.path
        import re
        sand_name = self.versioned_filename[index]
        output_name = os.path.join(sandbox, sand_name + "out")
        code = re.sub("((^|\\n)\\s*)(%LET\\s+WD\\s*=.*;)",
                      "\\1%LET WD=.;", code, flags=re.IGNORECASE)
        config = self.specific_configs[self.codefile + ".config"]
        to_pdf = config["pdf_output"].strip().upper()
        if to_pdf == "Y":
            code = "ODS PDF FILE='" + self.versioned_filename[index] + \
                   "." + sandbox + ".pdf';\nODS GRAPHICS ON;\n" + code
        prepend = config["code_prepend"].strip()
        if prepend != "":
            code = prepend + "\n" + code
        append = config["code_append"].strip()
        if append != "":
            code = code + "\n" + append + "\n"
        if to_pdf == "Y":
            code = code + "ODS PDF CLOSE;"
        self.write_text(code,
                        os.path.join(sandbox, sand_name))

        inoutfiles = '-SYSIN ' + sand_name + \
                     ' -ICON -NOSPLASH -NONEWS -LOG ' + \
                     sand_name + 'log -PRINT ' + sand_name + "out"
        runstring = '"' + self.SAS_prog + '" ' + inoutfiles
        if to_pdf == "Y":
            cwd = os.getcwd()
            runstring = [runstring, 'start ' +
                         os.path.join(cwd, sandbox,
                                      sand_name + '.' + sandbox + '.pdf')]
        return (runstring, output_name)

    def setup_python_runstring(self, code, sandbox, index):
        """
        Setup python runstring and make needed generic
        modifications to input code file.
        """
        import os.path
        import re
        sand_name = self.versioned_filename[index]
        output_name = os.path.join(sandbox, sand_name + "out")
        # Students tend to put dir() or ? in code.
        # We want to remove that.
        code = re.sub("((^|\\n)[:blank:]*)([?])",
                      "\\1### ?", code)
        code = re.sub("((^|\\n)[:blank:]*)help[(]",
                      "\\1### dir(", code)

        config = self.specific_configs[self.codefile + ".config"]
        prepend = config["code_prepend"].strip()
        prepend = re.sub("[*]{4}", "    ", prepend)
        prepend = re.sub("[*]{8}", "        ", prepend)
        if prepend != "":
            code = prepend + "\n" + code
        append = config["code_append"].strip()
        append = re.sub("[*]{4}", "    ", append)
        append = re.sub("[*]{8}", "        ", append)
        if append != "":
            code = code + "\n" + append + "\n"

        self.write_text(code,
                        os.path.join(sandbox, sand_name))

        inoutfiles = '< "' + sand_name + '"' + '1> "' + sand_name + 'out"' +\
            '2> "' + sand_name + 'err"'
        runstring = 'python ' + inoutfiles
        return (runstring, output_name)

    def get_dir_name(self, index):
        """
        Given the student index, return an appropriate sandbox directory name.
        If the email is available, use that, otherwise remove punctuation.
        """
        import re
        if self.email[index] != "":
            return self.email[index]
        f = self.student_name[index]
        return re.sub("[-~`!@#$%^&*()_+{}[\\]:;<>?,./]", "", f)

    def general_config_dialog(self):
        """
        Let user update the general configuration for the currently active
        directory (assignment).
        """
        import copy
        import time
        old_file_format = self.general_config['file_format']
        old_codefiles = self.general_config['codefiles']
        old_course_id = self.general_config['course_id']
        gconfig = copy.copy(self.general_config)
        title = "AutoGrader: General Configuration"
        self.conf_dialog = ConfigDialog(self, info=[self.general_config_setup,
                                                    gconfig],
                                        title=title)
        if self.conf_dialog.result is not None:
            self.general_config = self.conf_dialog.result
            self.general_config['config_mod_time'] = time.time()
            new_file_format = self.general_config['file_format'] != \
                old_file_format
            new_codefiles = self.general_config['codefiles'] != old_codefiles
            new_course_id = self.general_config['course_id'] != old_course_id
            self.update_for_general_config_nongui(new_file_format,
                                                  new_codefiles,
                                                  new_course_id)
            self.write_config_file(self.general_config_fname,
                                   self.general_config)
            filechange = new_file_format or new_codefiles
            self.update_gui(new_codefiles=filechange,
                            new_codefile_files=filechange)

    def update_for_general_config_nongui(self, new_file_format, new_codefiles,
                                         new_course_id):
        if new_file_format:
            self.set_file_format_info(self.general_config['file_format'])
        if new_codefiles:
            self.get_codefiles()
            if self.codefiles is not None:
                self.general_config['codefiles'] = ", ".join(self.codefiles)
        if new_file_format or new_codefiles:
            self.get_student_files(forceFirst=True)
            if len(self.student_name) == 0:
                self.current_code = None
            else:
                self.current_code = self.get_text(self.fullname[0])
        if new_course_id:
            self.read_roster()

    def get_text(self, filename):
        import codecs
        try:
            with codecs.open(filename, 'r', encoding='utf-8',
                             errors='replace') as myfile:
                text = myfile.read()
        except IOError:
            text = None
        return text

    def get_text_and_put_in_tab(self, filename, tabname, default,
                                disabled=False, SAS=False):
        """
        Get text and copy to a Text tab, using 'default' as the text if
        the file cannot be opened.
        If 'SAS' is True, replace chr(402) with "-", chr(12) with '\n'.
        'disabled' can be used to prevent editing.
        """
        text = self.get_text(filename)
        if SAS:
            text = text.replace(chr(402), "-").replace(chr(12), "\n")
        if disabled:
            tabname.configure(state='normal')
        tabname.delete(1.0, tk.END)
        if text is None:
            tabname.insert(tk.END, default)
        else:
            tabname.insert(tk.END, text+"\n\n\n")
        if disabled:
            tabname.configure(state='disabled')
        return text

    def write_text(self, text, fname, directory=None):
        """
        Write text to file directory/fname.
        As an aid to auto-save of letters when switching students,
        ignore this request if the directory does not exist.
        """
        import os.path
        import re
        import codecs

        if directory is not None:
            fname = os.path.join(directory, fname)
        if not os.path.exists(os.path.dirname(fname)):
            return

        # Somehow carriage returns are sneaking in and
        # causing problems in R.
        text = re.sub("\r+\n", "\n", text)

        try:
            with codecs.open(fname, 'w', encoding='utf-8',
                             errors='replace') as out:
                out.write(text)
        except IOError:
            messagebox.showwarning("File write error",
                                   "Could not write " + fname)
        return

    def specific_config_dialog(self):
        """
        Let user update the specific configuration for the currently active
        codefile (an element of the self.specific.configs dictionary).
        """
        import time
        if self.codefile is None:
            raise(Exception("Program error: editing with no codefiles"))
        cfb = self.codefile  # base
        cf = cfb + ".config"       # full
        title = "AutoGrader: Configuration for " + cfb
        self.conf_dialog = ConfigDialog(self, info=[self.specific_config_setup,
                                                    self.specific_configs[cf]],
                                        title=title)
        if self.conf_dialog.result is not None:
            self.specific_configs[cf] = self.conf_dialog.result
            self.specific_configs[cf]['config_mod_time'] = time.time()
            self.write_config_file(cf, self.specific_configs[cf])

    def init_gui(self):
        """ Build GUI """
        self.student_menu_built = False
        self.root.option_add('*tearOff', 'FALSE')
        self.root.title('AutoGrader: ' + self.dir)
        self.grid(column=0, row=0, sticky='nsew')

        # Menubar
        self.menubar = tk.Menu(self.root)
        self.menu_setup = tk.Menu(self.menubar)

        self.menu_setup.add_command(label='Choose directory...',
                                    command=self.choose_directory)
        self.menu_setup.add_command(label='General setup...',
                                    command=self.general_config_dialog)
        if self.codefiles is None:
            self.menu_setup.add_command(label='Setup codefile...',
                                        command=self.specific_config_dialog,
                                        state=tk.DISABLED)
        else:
            self.menu_setup.add_command(label="Setup " +
                                        self.codefiles[0] + "...",
                                        command=self.specific_config_dialog,
                                        state=tk.NORMAL)

        self.setup_specific_loc = 2  # index of submenu item
        self.menubar.add_cascade(menu=self.menu_setup, label='Configure')

        self.menu_action = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_action, label='Action')

        self.menu_exit = tk.Menu(self.menubar)
        self.menu_exit.add_command(label='Quit', command=self.on_quit)
        self.menubar.add_cascade(menu=self.menu_exit, label='Exit')

        self.root.config(menu=self.menubar)

        # Main GUI
        max_span = self.max_codefiles
        line = 0  # radio buttons for individual codefiles
        self.cf_index = tk.IntVar()
        self.cf_radio_dict = {}
        self.cf_text_dict = {}
        ### Need to init.gui when self.codefiles is None!!!!
        cf_n = len(self.codefiles)
        self.cf_index.set(0)
        self.cf_index.trace("w", self.choose_codefile)
        for i in range(self.max_codefiles):
            self.cf_text_dict[i] = tk.StringVar()
            if i >= cf_n:
                self.cf_text_dict[i].set('')
                self.cf_radio_dict[i] = \
                    tk.Radiobutton(self,
                                   variable=self.cf_index,
                                   value=i,
                                   textvariable=self.cf_text_dict[i],
                                   command=self.choose_codefile)
                self.cf_radio_dict[i].config(state=tk.DISABLED)
            else:
                self.cf_text_dict[i].set(self.codefiles[i])
                state = tk.ACTIVE if i == 0 else tk.NORMAL
                self.cf_radio_dict[i] = \
                    tk.Radiobutton(self,
                                   variable=self.cf_index,
                                   value=i,
                                   textvariable=self.cf_text_dict[i],
                                   state=state,
                                   command=self.choose_codefile)
            self.cf_radio_dict[i].grid(column=i, row=line, sticky='ew')
        self.cf_radio_dict[0].select()

        line += 1  # File count
        self.file_count = tk.Label(self,
                                   text="File count: " +
                                   str(len(self.filename)))
        self.file_count.grid(column=0, row=line, columnspan=max_span,
                             sticky='w')

        # Drop down menu of student files
        self.chosen_file = tk.StringVar(self)
        if self.file_label is None or len(self.file_label) == 0:
            first = ''
            labels = ['']
        else:
            first = self.file_label[0]
            labels = self.file_label
        self.chosen_file.set(first)
        # Reference: https://stackoverflow.com/questions/22462654/getting-the-
        # choice-of-optionmenu-right-after-selection-python
        self.chosen_file.trace("w", self.choose_student_file)
        self.dropdownMenu = tk.OptionMenu(self, self.chosen_file,
                                          *labels)
        self.dropdownMenu.grid(column=1, row=line, columnspan=1,
                               sticky='ew')
        self.student_menu_built = True

        # action buttons
        self.run_one_b = tk.Button(self, text='Run one',
                                   command=self.run_one)
        self.run_one_b.grid(column=2, row=line, columnspan=1)
        self.run_all_b = tk.Button(self, text='Run pending',
                                   command=self.run_all)
        self.run_all_b.grid(column=3, row=line, columnspan=1)

        line += 1
        ttk.Separator(self, orient='horizontal').grid(column=0, row=line,
                                                      columnspan=max_span,
                                                      sticky='ew')

        line += 1  # Notebook of codefiles and results
        self.nb_width = 1200
        self.nb_cwidth = int(self.nb_width / 8) - 3
        nb = self.notebook = ttk.Notebook(self, height=600,
                                          width=self.nb_width)
        self.notebook.grid(column=0, row=line, columnspan=max_span,
                           sticky="nsew")

        self.input_frame = tk.Frame(nb)
        self.input_analysis_frame = tk.Frame(nb)
        self.messages_frame = tk.Frame(nb)
        self.output_frame = tk.Frame(nb)
        self.output_analysis_frame = tk.Frame(nb)
        self.letter_frame = tk.Frame(nb)

        self.input_frame.grid(row=line, column=0, sticky="nsew")
        self.input_analysis_frame.grid(row=line, column=0, sticky="nsew")
        self.messages_frame.grid(row=line, column=0, sticky="nsew")
        self.output_frame.grid(row=line, column=0, sticky="nsew")
        self.output_analysis_frame.grid(row=line, column=0, sticky="nsew")
        self.letter_frame.grid(row=line, column=0, sticky="nsew")

        self.sbi = tk.Scrollbar(self.input_frame)
        self.sbia = tk.Scrollbar(self.input_analysis_frame)
        self.sbm = tk.Scrollbar(self.messages_frame)
        self.sbo = tk.Scrollbar(self.output_frame)
        self.sboa = tk.Scrollbar(self.output_analysis_frame)
        self.sbl = tk.Scrollbar(self.letter_frame)

        self.input = tk.Text(self.input_frame, bg="lightblue",
                             width=self.nb_cwidth, height=41,
                             yscrollcommand=self.sbi.set)
        self.input_analysis = tk.Text(self.input_analysis_frame,
                                      bg="lightblue",
                                      width=self.nb_cwidth, height=41,
                                      yscrollcommand=self.sbia.set)
        self.messages = tk.Text(self.messages_frame, bg="lightblue",
                                width=self.nb_cwidth, height=41,
                                yscrollcommand=self.sbm.set)
        self.output = tk.Text(self.output_frame, bg="lightblue",
                              width=self.nb_cwidth, height=41,
                              yscrollcommand=self.sbo.set)
        self.output_analysis = tk.Text(self.output_analysis_frame,
                                       bg="lightblue",
                                       width=self.nb_cwidth, height=41,
                                       yscrollcommand=self.sboa.set)
        self.letter = tk.Text(self.letter_frame,
                              bg="lightblue",
                              width=self.nb_cwidth, height=41,
                              yscrollcommand=self.sbl.set)

        self.sbi.grid(row=0, column=1, sticky="ens")
        self.input.grid(row=0, column=0, columnspan=1, sticky="ewnw")
        self.sbia.grid(row=0, column=1, sticky="ens")
        self.input_analysis.grid(row=0, column=0, columnspan=1, sticky="ewnw")
        self.sbm.grid(row=0, column=1, sticky="ens")
        self.messages.grid(row=0, column=0, columnspan=1, sticky="ewnw")
        self.sbo.grid(row=0, column=1, sticky="ens")
        self.output.grid(row=0, column=0, columnspan=1, sticky="ewnw")
        self.sboa.grid(row=0, column=1, sticky="ens")
        self.output_analysis.grid(row=0, column=0, columnspan=1, sticky="ewnw")
        self.sbl.grid(row=0, column=1, sticky="ens")
        self.letter.grid(row=0, column=0, columnspan=1, sticky="ewnw")

        self.sbi.config(command=self.input.yview)
        self.sbia.config(command=self.input_analysis.yview)
        self.sbm.config(command=self.messages.yview)
        self.sbo.config(command=self.output.yview)
        self.sboa.config(command=self.output_analysis.yview)
        self.sbl.config(command=self.letter.yview)

        nb.add(self.input_frame, text="input", sticky="nsw")
        nb.add(self.input_analysis_frame, text="input analysis")
        nb.add(self.messages_frame, text="messages")
        nb.add(self.output_frame, text="output")
        nb.add(self.output_analysis_frame, text="output analysis")
        nb.add(self.letter_frame, text="letter")

        # self.notebook.grid(column=0, row=line, columnspan=max_span)
        if self.current_code is None:
            self.input.insert(tk.END, "(No input)")
        else:
            self.input.insert(tk.END, self.current_code)
        self.input_analysis.insert(tk.END, "(No input analysis)")
        self.messages.configure(state='normal')
        self.messages.insert(tk.END, "(No message)")
        self.messages.configure(state='disabled')
        self.output.insert(tk.END, "(No output)")
        self.output_analysis.insert(tk.END, "(No output analysis)")

        line += 1  # Close button
        self.close_but = ttk.Button(self, text='Exit autoGrader',
                                    command=self.root.destroy)
        self.close_but.grid(column=0, row=line, columnspan=max_span)

        # Fix spacing
        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)

        return


class ConfigDialog(Dialog):
    """ Configuration input window for R Grader.
        'info' should be [config_setup, config].
        config_setup entries are 0=id, 1=label, 2=type, 3=dim, 4=default.
        config dictionary entries are intexed by the 'id'.
    """

    def body(self, master):
        self.d_widgets = {}
        for i in range(len(self.info[0])):
            setup = self.info[0][i]
            id = setup[0]
            data = self.info[1][id]
            if id == 'config_mod_time':
                pass
            elif setup[2] == 'int':
                self.d_widgets[id] = ttk.Entry(master)
            elif setup[2] == 'box':
                self.d_widgets[id] = tk.Text(master,
                                             height=setup[3][0],
                                             width=setup[3][1])
            elif setup[2] == 'line':
                self.d_widgets[id] = tk.Entry(master,
                                              width=setup[3])
            else:
                raise(Exception('bad config setup type'))
            ttk.Label(master, text=setup[1]).pack()
            self.d_widgets[id].pack(padx=5)
            ipos = tk.END if setup[2] == 'box' else 0
            self.d_widgets[id].insert(ipos, data)

    def validate(self):
        ii = None
        try:
            for i in range(len(self.info[0])):
                ii = i
                thisInfo = self.info[0][i]
                thisWidget = self.d_widgets[thisInfo[0]]
                if thisInfo[2] == 'int':
                    thisData = thisWidget.get().strip()
                    if thisData != '':
                        int(thisData)
            return 1
        except ValueError:
            msg = '"' + self.info[0][ii][1] + '" requires blank or an ' + \
                  'integer.  Please try again.'
            # self.grab_set()
            messagebox.showwarning("Bad input", msg)
            #  self.wait_window()
            return 0

    def apply(self):
        self.result = {}
        for i in range(len(self.info[0])):
            thisInfo = self.info[0][i]
            thisWidget = self.d_widgets[thisInfo[0]]
            id = thisInfo[0]
            if thisInfo[2] == 'int':
                thisData = thisWidget.get().strip()
                if thisData == '':
                    self.result[id] = thisInfo[4]
                else:
                    self.result[id] = int(thisData)
            elif thisInfo[2] == 'box':
                value = self.d_widgets[id].get(1.0, tk.END)
                if len(value) > 0 and value[-1] == "\n":
                    value = value[:-1]
                self.result[id] = value
            elif thisInfo[2] == 'line':
                value = self.d_widgets[id].get()
                if len(value) > 0 and value[-1] == "\n":
                    value = value[:-1]
                self.result[id] = value
            else:
                raise(Exception('bad config setup type'))


if __name__ == '__main__':
    root = tk.Tk()
    AutoGrader(root)
    root.mainloop()

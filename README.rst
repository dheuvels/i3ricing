
Abstract
********

A collection of `i3ipc <https://pypi.org/project/i3ipc/>`_ code, used
to simulate I3 commands that do not exist or do not work, as I’d like
them to work. Examples from my I3 config:

..

   ::

      bindsym $mod+Shift+Right exec (..)/i3ricing.py Mover.focused_container_right
      bindsym $mod+Shift+Left  exec (..)/i3ricing.py Mover.focused_container_left

      bindsym $mod+Shift+Mod1+Right exec (..)/i3ricing.py Mover.focused_container_to_next_ws
      bindsym $mod+Shift+Mod1+Left  exec (..)/i3ricing.py Mover.focused_container_to_previous_ws

      bindsym $mod+Mod1+Return exec (..)/i3ricing.py Launcher.new_workspace
      bindsym $mod+r exec /(..)/i3ricing.py Launcher.on_focused "exec dmenu_run -m {} -fn '-*-terminus-*-*-normal-*-*-180-*-*-*-*-*-*'" run=True


API
***

The *i3ricing* module contains a main guard that exposes the Classes
on the commandline like this:

::

   ./i3ricing.py Class.method [positional_arg1, positional_arg2, ..] [named_arg1=value1, named_arg2=value2, ..]


Classes
*******

**class i3ricing.Mover**

   Commands for moving containers and workspaces.

   **focused_container_right()**

      Moves the focused container right. This is an amendment to the
      following *i3-ipc* command:

      ::

         i3-msg "move right"

      With multiple containers in an horizontal split (siblings) the
      above command moves the focused container right within the
      siblings. However if the focused container is the rightmost
      sibling, it will jump to the next output (not the next workspace
      as I would expect). This is annoying as it even ignores existing
      workspaces on the originating output.

      There was a `pull request
      <https://github.com/i3/i3/issues/2587>`_ that was merged around
      4.18, which added the desired functionality to the *focus*
      command:

      ::

         i3-msg "focus next sibling"

      However it is not available in the *move* command and the *next
      sibling* and it will not change the focus across workspaces.

      *focused_container_right()* moves right, until the container is
      the rightmost sibling and then moves it to the next workspace
      (actually by calling *focused_container_to_next_ws()*).

      :Returns:
         The result of *i3ipc.Connection.command()* or the result of
         *focused_container_to_next_ws()*.

   **focused_container_left()**

      Same as *focused_container_right()*, but in the other direction.

   **focused_container_to_next_ws()**

      Move the focused container to the next workspace. This is an
      amendment to the following *i3-ipc* commands (I have seen once
      or twice on Reddit).

      ::

         i3-msg "move container to workspace next(_on_output); workspace next(_on_output)"

      The above commands will move the focused container, but only to
      existing workspaces. When using workspace assignments (e.g.
      workspace 1 to 9 assigned to output HDMIx) this doesn’t feel
      right, because a container on workspace 1 cannot be moved to
      workspace 2, if that workspace does not exist already (and I3
      will have closed workspace 2 automatically, if there were no
      other containers on it).

      *focused_container_to_next_ws()* will move the container to the
      next workspace, regardless if it has to be created or if it
      already exists.

      :Returns:
         The result of *i3ipc.Connection.command()*.

   **focused_container_to_previous_ws()**

      Same as *focused_container_to_next_ws()*, but in the other
      direction.

**class i3ricing.Launcher**

   Commands for creating containers and workspaces.

   **new_workspace()**

      Opens a new workspace with the next free workspace number. This
      is an amendment to the following *i3-ipc* commands.

      ::

         i3-msg "workspace $(i3-msg -t get_workspaces \|jq '[.[].num] \|max+1')"

      The idea is to open a new workspace right of the focused one.
      However the *i3-msg* commands above ignore gaps in existing
      workspace numbers and fail in multi monitor configurations.

      :Returns:
         The result of *i3ipc.Connection.command()*.

   **on_focused(cmd, attrib=None, run=True)**

      Takes a string with a `formatting placeholder
      <https://docs.python.org/3/library/string.html#format-specification-mini-language>`_
      and replaces it with an attribute value from the `i3ipc Con
      object
      <https://i3ipc-python.readthedocs.io/en/latest/con.html#>`_
      representing the focused output.

      The idea is to tell X11 programs where to find the focused
      output by providing XRandR information on the commandline. In
      some cases this can be messy due to different interpretations of
      XRandR data. (E.g. *dmenu* where I ended up, recompiling it. See
      *resources* folder.)

      :Parameters:
         * **cmd** – The command with a placeholder. E.g.: “exec
            my_fancy_prog –output {}”

         * **attrib** – An attribute of *i3ipc.Con* to substitute the
            placeholder in *cmd*. If *None*, the value returned by
            *BaseI3.get_focused_output_idx()* will be used.

         * **run** – If *True*, the resulting command will be passed
            to i3ipc, if *False* the command is returned.

      :Returns:
         The result of *i3ipc.Connection.command()* if *run* is *True*
         or the command string if not.

      :Raises:
         IndexError if *cmd* contains an invalid format string.

      :Raises:
         AttributeError if *attrib* contains a name that is not an
         attribute of *i3ipc.OutputReply*.

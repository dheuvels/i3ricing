#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import i3ipc
import re
import sys

__version__ = "0.1"
OUTPUT_TYPE = "output"
STASH_OUTPUT = "__i3"


class BaseI3:
    def __init__(self):
        self.conn = i3ipc.Connection()
        self.i3tree = self.conn.get_tree()

        # I3 nodes that represent an output. These are the output representations in the i3 tree. The node name builds the bridge to xrandr.
        i3_outputs = [node for node in self.i3tree.nodes if node.type == OUTPUT_TYPE and node.name != STASH_OUTPUT]
        # Sort nodes by their horizontal positions, so that the index reflects the position left to right.
        self.i3_outputs = sorted(i3_outputs, key=lambda op: op.rect.x)

        # `OutputReply` objects from `Connection.get_outputs()`. This is the output representation in xrandr (or what i3ipc reveals about it).
        randr_outputs = [output for output in self.conn.get_outputs() if output.active]
        # Sort the primary output to the first position (look at `get_focused_output_idx()` why).
        # Python's `sorted()` function is stable, so that we will not change the order of the non-primary outputs.
        self.randr_outputs = sorted(randr_outputs, key=lambda op: 0 if op.primary else 1)

        self.workspaces = sorted(self.i3tree.workspaces(), key=lambda ws: (ws.rect.x, ws.num))

    def get_focused_output(self):
        """ :return: The focused output in its `i3ipc.Con` representation. """
        for output in self.i3_outputs:
            if output.find_focused():
                return output
        return None

    def get_focused_output_idx(self):
        """
        :return: The focused output index based on the `i3ipc.Connection.OutputReply` representation
                 returned by `i3ipc.Connection.get_outputs()`.
                 I need this for the `-m` switch in dmenu which expects a "monitor number" (whatever that is).
                 There are some leftovers from xinerama in dmenu and the number seems to come from what is returned
                 by `xrandr --listactivemonitors`.
                 I'm not sure, if `get_outputs()` always returns the same order as `xrandr --listactivemonitors`.
                 Anyway, as long as I put the primary display first and let the rest unchanged, it seems to work.
        """
        focused_output = self.get_focused_output()
        for idx, output in enumerate(self.randr_outputs):
            if focused_output.name == output.name:
                return idx
        return 0

    def find_next_workspace(self, find_new=False):
        """
        Finds the next larger workspace number starting from the workspace that displays the focused container.

        :param find_new: (bool) Find a workspace number that is currently not in use.
        :return: workspace number
        """
        idx = self.workspaces.index(self.i3tree.find_focused().workspace())
        idx_max = len(self.workspaces) - 1

        while find_new and idx < idx_max:
            # If we are looking for a free workspace and there is a gap, we have found it.
            if self.workspaces[idx+1].num > self.workspaces[idx].num + 1:
                return self.workspaces[idx].num + 1
            idx += 1

        return self.workspaces[idx].num + 1

    def find_previous_workspace(self, find_new=False):
        """
        Finds the next smaller workspace number starting from the workspace that displays the focused container.

        :param find_new: (bool) Find a workspace number that is currently not in use.
        :return: workspace number
        """
        idx = self.workspaces.index(self.i3tree.find_focused().workspace())
        idx_max = len(self.workspaces) - 1

        while find_new and idx > 0:
            # If we are looking for a free workspace and there is a gap, we have found it.
            if self.workspaces[idx-1].num < self.workspaces[idx].num - 1:
                return self.workspaces[idx].num - 1
            idx -= 1

        if self.workspaces[idx].num > 1:
            return self.workspaces[idx].num - 1
        else:
            return self.workspaces[idx_max].num + 1 if find_new else self.workspaces[idx_max].num


class Mover(BaseI3):
    """ Commands for moving containers and workspaces.
    """

    def focused_container_right(self):
        """
        Moves the focused container right. This is an amendment to the following `i3-ipc` command:

        .. code-block:: python

            i3-msg "move right"

        With multiple containers in an horizontal split (siblings) the above command moves the focused container right
        within the siblings. However if the focused container is the rightmost sibling, it will jump to the next output
        (not the next workspace as I would expect). This is annoying as it even ignores existing workspaces on the
        originating output.

        There was a `pull request`_ that was merged around 4.18, which added the desired functionality to the `focus`
        command:

        .. code-block:: python

            i3-msg "focus next sibling"

        However it is not available in the `move` command and the `next sibling` and it will not change the focus
        across workspaces.

        `focused_container_right()` will move the to the next workspace, if it was the rightmost container (actually by
        calling `focused_container_to_next_ws()`).

        :return: The result of `i3ipc.Connection.command()` or the result of `focused_container_to_next_ws()`.

        .. _pull request: https://github.com/i3/i3/issues/2587
        """
        con = self.i3tree.find_focused()

        if con.parent.orientation == "horizontal" and con.parent.nodes[-1].id == con.id:
            return self.focused_container_to_next_ws()
        else:
            return self.conn.command("move right")

    def focused_container_left(self):
        """ Same as `focused_container_right()`, but in the other direction. """
        con = self.i3tree.find_focused()

        if con.parent.orientation == "horizontal" and con.parent.nodes[0].id == con.id:
            return self.focused_container_to_previous_ws()
        else:
            return self.conn.command("move left")

    def focused_container_to_next_ws(self):
        """
        Move the focused container to the next workspace.
        This is an amendment to the following `i3-ipc` commands (I have seen once or twice on Reddit).

        .. code-block:: python

            i3-msg "move container to workspace next(_on_output); workspace next(_on_output)"

        The above commands will move the focused container, but only to existing workspaces. When using workspace
        assignments (e.g. workspace 1 to 9 assigned to output HDMIx) this doesn't feel right, because a container
        on workspace 1 cannot be moved to workspace 2, if that workspace does not exist already (and I3 will have closed
        workspace 2 automatically, if there were no other containers on it).

        `focused_container_to_next_ws()` will move the container to the next workspace, regardless if it has to
        be created or if it already exists.

        :return:  The result of `i3ipc.Connection.command()`.
        """
        ws_num = self.find_next_workspace()
        cmd = "move container to workspace number {}; workspace number {}".format(ws_num, ws_num)
        return self.conn.command(cmd)

    def focused_container_to_previous_ws(self):
        """ Same as `focused_container_to_next_ws()`, but in the other direction. """
        ws_num = self.find_previous_workspace()
        cmd = "move container to workspace number {}; workspace number {}".format(ws_num, ws_num)
        return self.conn.command(cmd)


class Launcher(BaseI3):
    """ Commands for creating containers and workspaces.
    """

    def new_workspace(self):
        """
        Opens a new workspace with the next free workspace number.
        This is an amendment to the following `i3-ipc` commands.

        .. code-block:: python

            i3-msg "workspace $(i3-msg -t get_workspaces \|jq '[.[].num] \|max+1')"

        The idea is to open a new workspace right of the focused one. However the `i3-msg` commands above ignore gaps in
        existing workspace numbers and fail in multi monitor configurations.

        :return: The result of `i3ipc.Connection.command()`.
        """
        cmd = "workspace number {}".format(self.find_next_workspace(find_new=True))
        return self.conn.command(cmd)

    def on_focused(self, cmd, attrib=None, run=True):
        """
        Takes a string with a `formatting placeholder`_ and replaces it with an attribute value from the
        `i3ipc Con object`_ representing the focused output.

        The idea is to tell X11 programs where to find the focused output by providing XRandR information on the
        commandline. In some cases this can be messy due to different interpretations of XRandR data. (E.g. `dmenu`
        where I ended up, recompiling it. See `resources` folder.)

        :param cmd:    The command with a placeholder. E.g.: "exec my_fancy_prog --output {}"
        :param attrib: An attribute of `i3ipc.Con` to substitute the placeholder in `cmd`.
                       If `None`, the value returned by `BaseI3.get_focused_output_idx()` will be used.
        :param run:    If `True`, the resulting command will be passed to i3ipc, if `False` the command is returned.
        :return:       The result of `i3ipc.Connection.command()` if `run` is `True` or the command string if not.

        :raises: IndexError if `cmd` contains an invalid format string.
        :raises: AttributeError if `attrib` contains a name that is not an attribute of `i3ipc.OutputReply`.

        .. _formatting placeholder: https://docs.python.org/3/library/string.html#format-specification-mini-language
        .. _i3ipc Con object: https://i3ipc-python.readthedocs.io/en/latest/con.html#
        """
        if attrib:
            output = self.get_focused_output()
            subst_value = getattr(output, attrib)
        else:
            output_idx = self.get_focused_output_idx()
            subst_value = output_idx

        cmd_final = cmd.format(subst_value)
        if run:
            return self.conn.command(cmd_final)
        else:
            return cmd_final


def main():
    """
    The `i3ricing` module contains a main guard that exposes the Classes on the commandline like this:

    .. code-block:: python

        ./i3ricing.py Class.method [positional_arg1, positional_arg2, ..] [named_arg1=value1, named_arg2=value2, ..]

    """
    cmdline_args = sys.argv[1:]
    args = []
    kwargs = {}
    err = None

    if cmdline_args:
        for arg in cmdline_args:
            split = arg.split("=")
            if len(split) > 1:
                kwargs[split[0]] = split[1]
            else:
                if kwargs:
                    err = "Positional arg '{}' found after keyword args.".format(arg)
                else:
                    args.append(arg)
    else:
        err = "Empty command argument list."
    if args:
        if not re.match(r'\w+\.\w+', args[0]):
            err = "Expected 'class.method' as first argument. Found '{}'.".format(args[0])
    else:
        err = "What should I run? Expected 'class.method' as first argument."

    if err:
        print("Usage: {} class.method [parg1 parg2 .. ] [ kwarg1=kwvarg1 kwarg2=kwarg2 .. ]")
        print(err, file=sys.stderr)
        sys.exit(1)
    else:
        (class_name, method_name) = args.pop(0).split('.')

    _class = getattr(sys.modules[__name__], class_name)
    _method = getattr(_class, method_name)
    _method(_class(), *args, **kwargs)


if __name__ == "__main__":
    main()

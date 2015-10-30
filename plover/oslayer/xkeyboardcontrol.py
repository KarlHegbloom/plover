# Copyright (c) 2010 Joshua Harlan Lifton.
# See LICENSE.txt for details.
#
# keyboardcontrol.py - capturing and injecting X keyboard events
#
# This code requires the X Window System with the 'XInput2' and 'XTest'
# extensions and python-xlib with support for said extensions.
#

"""Keyboard capture and control using Xlib.

This module provides an interface for basic keyboard event capture and
emulation. Set the key_up and key_down functions of the
KeyboardCapture class to capture keyboard input. Call the send_string
and send_backspaces functions of the KeyboardEmulation class to
emulate keyboard input.

For an explanation of keycodes, keysyms, and modifiers, see:
http://tronche.com/gui/x/xlib/input/keyboard-encoding.html

"""

import sys
import threading

from Xlib import X, XK, display, threaded
from Xlib.ext import xinput, xtest
from Xlib.ext.ge import GenericEventCode
from Xlib.protocol import rq, event

XINPUT_DEVICE_ID = xinput.AllMasterDevices
XINPUT_EVENT_MASK = xinput.KeyPressMask | xinput.KeyReleaseMask

keyboard_capture_instances = []

KEYCODE_TO_KEY = {
    # Function row.
    67: "F1",
    68: "F2",
    69: "F3",
    70: "F4",
    71: "F5",
    72: "F6",
    73: "F7",
    74: "F8",
    75: "F9",
    76: "F10",
    95: "F11",
    96: "F12",
    # Number row.
    49: "`",
    10: "1",
    11: "2",
    12: "3",
    13: "4",
    14: "5",
    15: "6",
    16: "7",
    17: "8",
    18: "9",
    19: "0",
    20: "-",
    21: "=",
    51: "\\",
    # Upper row.
    24: "q",
    25: "w",
    26: "e",
    27: "r",
    28: "t",
    29: "y",
    30: "u",
    31: "i",
    32: "o",
    33: "p",
    34: "[",
    35: "]",
    # Home row.
    38: "a",
    39: "s",
    40: "d",
    41: "f",
    42: "g",
    43: "h",
    44: "j",
    45: "k",
    46: "l",
    47: ";",
    48: "'",
    # Bottom row.
    52: "z",
    53: "x",
    54: "c",
    55: "v",
    56: "b",
    57: "n",
    58: "m",
    59: ",",
    60: ".",
    61: "/",
    # Space bar.
    65: "space",
}

KEY_TO_KEYCODE = dict(zip(KEYCODE_TO_KEY.values(), KEYCODE_TO_KEY.keys()))

class KeyboardCapture(threading.Thread):
    """Listen to keyboard press and release events."""

    def __init__(self, suppressed_keys):
        """Prepare to listen for keyboard events."""
        threading.Thread.__init__(self)
        self.context = None
        self.suppressed_keys = suppressed_keys
        self.is_suppressed = False

        # Assign default callback functions.
        self.key_down = lambda x: True
        self.key_up = lambda x: True

        # Get references to the display.
        self.display = display.Display()
        self.window = self.display.screen().root

        # Find XTest keyboard device ID, so we can ignore its events.
        self.xtest_keyboard = 0
        for devinfo in self.display.xinput_query_device(xinput.AllDevices).devices:
            if 'Virtual core XTEST keyboard' == devinfo.name:
                self.xtest_keyboard = devinfo.deviceid
                break

    def run(self):
        self.window.xinput_select_events(((XINPUT_DEVICE_ID, XINPUT_EVENT_MASK),))
        while True:
            event = self.display.next_event()
            if event.type != GenericEventCode:
                continue
            if not event.evtype in (xinput.KeyPress, xinput.KeyRelease):
                continue
            keycode = event.data.detail
            modifiers = event.data.mods.effective_mods & ~0b10000 & 0xFF
            sourceid = event.data.sourceid
            # Ignore XTest events.
            if self.xtest_keyboard == sourceid:
                continue
            if 0 != modifiers:
                continue
            # Ignore repeat events.
            if 0 != (event.data.flags & xinput.KeyRepeat):
                continue
            key = KEYCODE_TO_KEY.get(keycode, None)
            if not key in self.suppressed_keys:
                # Not a supported/suppressed key, ignore...
                continue
            # ...or pass it on to a callback method.
            if event.evtype == xinput.KeyPress:
                self.key_down(key)
            elif event.evtype == xinput.KeyRelease:
                self.key_up(key)

    def start(self):
        """Starts the thread after registering with a global list."""
        keyboard_capture_instances.append(self)
        threading.Thread.start(self)

    def cancel(self):
        """Stop listening for keyboard events."""
        self.display.flush()
        if self in keyboard_capture_instances:
            keyboard_capture_instances.remove(self)

    def can_suppress_keyboard(self):
        return True

    def grab_key(self, keycode):
        self.window.xinput_grab_keycode(XINPUT_DEVICE_ID,
                                        X.CurrentTime,
                                        keycode,
                                        xinput.GrabModeAsync,
                                        xinput.GrabModeAsync,
                                        True,
                                        XINPUT_EVENT_MASK,
                                        (0, X.Mod2Mask))

    def ungrab_key(self, keycode):
        self.window.xinput_ungrab_keycode(XINPUT_DEVICE_ID,
                                          keycode,
                                          (0, X.Mod2Mask))

    def suppress_keyboard(self, suppress):
        if self.is_suppressed == suppress:
            return
        if suppress:
            fn = self.grab_key
        else:
            fn = self.ungrab_key
        for key in self.suppressed_keys:
            fn(KEY_TO_KEYCODE[key])
        self.display.sync()
        self.is_suppressed = suppress

    def is_keyboard_suppressed(self):
        return self.is_suppressed


class KeyboardEmulation(object):
    """Emulate keyboard events."""

    def __init__(self):
        """Prepare to emulate keyboard events."""
        self.display = display.Display()
        self.modifier_mapping = self.display.get_modifier_mapping()
        # Determine the backspace keycode.
        backspace_keysym = XK.string_to_keysym('BackSpace')
        self.backspace_keycode, mods = self._keysym_to_keycode_and_modifiers(
                                                backspace_keysym)
        self.time = 0

    def send_backspaces(self, number_of_backspaces):
        """Emulate the given number of backspaces.

        The emulated backspaces are not detected by KeyboardCapture.

        Argument:

        number_of_backspace -- The number of backspaces to emulate.

        """
        for x in xrange(number_of_backspaces):
            self._send_keycode(self.backspace_keycode)

    def send_string(self, s):
        """Emulate the given string.

        The emulated string is not detected by KeyboardCapture.

        Argument:

        s -- The string to emulate.

        """
        for char in s:
            keysym = ord(char)
            keycode, modifiers = self._keysym_to_keycode_and_modifiers(keysym)
            if keycode is not None:
                self._send_keycode(keycode, modifiers)
                self.display.sync()

    def send_key_combination(self, combo_string):
        """Emulate a sequence of key combinations.

        Argument:

        combo_string -- A string representing a sequence of key
        combinations. Keys are represented by their names in the
        Xlib.XK module, without the 'XK_' prefix. For example, the
        left Alt key is represented by 'Alt_L'. Keys are either
        separated by a space or a left or right parenthesis.
        Parentheses must be properly formed in pairs and may be
        nested. A key immediately followed by a parenthetical
        indicates that the key is pressed down while all keys enclosed
        in the parenthetical are pressed and released in turn. For
        example, Alt_L(Tab) means to hold the left Alt key down, press
        and release the Tab key, and then release the left Alt key.

        """
        # Convert the argument into a sequence of keycode, event type pairs
        # that, if executed in order, would emulate the key
        # combination represented by the argument.
        keycode_events = []
        key_down_stack = []
        current_command = []
        for c in combo_string:
            if c in (' ', '(', ')'):
                keystring = ''.join(current_command)
                keysym = XK.string_to_keysym(keystring)
                keycode, mods = self._keysym_to_keycode_and_modifiers(keysym)
                current_command = []
                if keycode is None:
                    continue
                if c == ' ':
                    # Record press and release for command's key.
                    keycode_events.append((keycode, X.KeyPress))
                    keycode_events.append((keycode, X.KeyRelease))
                elif c == '(':
                    # Record press for command's key.
                    key_down_stack.append(keycode)
                    keycode_events.append((keycode, X.KeyPress))
                elif c == ')':
                    # Record press and release for command's key and
                    # release previously held key.
                    keycode_events.append((keycode, X.KeyPress))
                    keycode_events.append((keycode, X.KeyRelease))
                    if len(key_down_stack):
                        keycode = key_down_stack.pop()
                        keycode_events.append((keycode, X.KeyRelease))
            else:
                current_command.append(c)
        # Record final command key.
        keystring = ''.join(current_command)
        keysym = XK.string_to_keysym(keystring)
        keycode, mods = self._keysym_to_keycode_and_modifiers(keysym)
        if keycode is not None:
            keycode_events.append((keycode, X.KeyPress))
            keycode_events.append((keycode, X.KeyRelease))
        # Release all keys.
        for keycode in key_down_stack:
            keycode_events.append((keycode, X.KeyRelease))

        # Emulate the key combination by sending key events.
        for keycode, event_type in keycode_events:
            xtest.fake_input(self.display, event_type, keycode)
            self.display.sync()

    def _send_keycode(self, keycode, modifiers=0):
        """Emulate a key press and release.

        Arguments:

        keycode -- An integer in the inclusive range [8-255].

        modifiers -- An 8-bit bit mask indicating if the key pressed
        is modified by other keys, such as Shift, Capslock, Control,
        and Alt.

        """
        self._send_key_event(keycode, modifiers, event.KeyPress)
        self._send_key_event(keycode, modifiers, event.KeyRelease)

    def _send_key_event(self, keycode, modifiers, event_class):
        """Simulate a key press or release.

        These events are not detected by KeyboardCapture.

        Arguments:

        keycode -- An integer in the inclusive range [8-255].

        modifiers -- An 8-bit bit mask indicating if the key pressed
        is modified by other keys, such as Shift, Capslock, Control,
        and Alt.

        event_class -- One of Xlib.protocol.event.KeyPress or
        Xlib.protocol.event.KeyRelease.

        """
        target_window = self.display.get_input_focus().focus
        # Make sure every event time is different than the previous one, to
        # avoid an application thinking its an auto-repeat.
        self.time = (self.time + 1) % 4294967295
        key_event = event_class(detail=keycode,
                                 time=self.time,
                                 root=self.display.screen().root,
                                 window=target_window,
                                 child=X.NONE,
                                 root_x=1,
                                 root_y=1,
                                 event_x=1,
                                 event_y=1,
                                 state=modifiers,
                                 same_screen=1
                                 )
        target_window.send_event(key_event)

    def _keysym_to_keycode_and_modifiers(self, keysym):
        """Return a keycode and modifier mask pair that result in the keysym.

        There is a one-to-many mapping from keysyms to keycode and
        modifiers pairs; this function returns one of the possibly
        many valid mappings, or the tuple (None, None) if no mapping
        exists.

        Arguments:

        keysym -- A key symbol.

        """
        keycodes = self.display.keysym_to_keycodes(keysym)
        if len(keycodes) > 0:
            keycode, offset = keycodes[0]
            modifiers = 0
            if offset == 1 or offset == 3 or offset == 5:
                # The keycode needs the Shift modifier.
                modifiers |= X.ShiftMask
            if offset == 4 or offset == 5:
                # 3rd (AltGr) level.
                modifiers |= X.Mod5Mask
            if offset == 2 or offset == 3:
                # The keysym is in group Group 2 instead of Group 1.
                for i, mod_keycodes in enumerate(self.modifier_mapping):
                    if keycode in mod_keycodes:
                        modifiers |= (1 << i)
            return (keycode, modifiers)
        return (None, None)


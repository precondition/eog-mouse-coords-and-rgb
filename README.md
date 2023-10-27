# Mouse Coords and RGB Plugin for Eye of Gnome (EOG), Gnome's image viewer

This plugin adds a status bar showing the image coordinates of the pixel your cursor hovers around, as well as the RGB values of that pixel.
This plugin is made for versions of `eog` running on GTK version 3. Practically speaking, it has only been tested on Eye of Gnome version 42.

![showcase](showcase.webm)

## Usage

Copy `mouse-coords-and-rgb.py` and `mouse-coords-and-rgb.plugin` into `~/.local/share/eog/plugins` if you're on Linux, then make sure to enable the plugin by opening the hamburger menu and going into “Setting” and choosing the “Plugins” tab where “Mouse Coordinates and RGB” should hopefully be listed.

## History

Originally, this plugin was written by [sdaau](https://sourceforge.net/u/sdaau/profile/) for the Gnome2 version of `eog` and his code is available in his [“SdaauBckp” repository on SourceForge](https://sourceforge.net/p/sdaaubckp/code/HEAD/tree/extensions/eog/mousecoords) ([WebArchive link](https://web.archive.org/web/20231027205517/https://sourceforge.net/p/sdaaubckp/code/HEAD/tree/extensions/eog/mousecoords/)). I (precondition) updated the code to be compatible with Gnome3. In addition to merely bringing the code up-to-date, I removed info related to the scaled image size, the zoom level, and the `eog` window coords because I found them to be unnecessary noise. In their place, I added RGB info to get something closer to the status bar of the OpenCV image/video viewer. I also removed the feature that lets you copy the mouse coords into clipboard since that was implemented with the obsolete “UI Manager” framework and I couldn't be bothered to figure out how to re-implement this feature I don't need in the new framework.

The code could definitely make use of a clean-up and refactor but it works for me ¯\\_ (ツ)_/¯

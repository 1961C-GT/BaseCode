
INSTANCE = None


class EngColors:
    def __init__(self, use_dark=True):
        if use_dark:
            self.background        = "#22252b"
            self.background_accent = "#191b1f"
            self.background_dialog = "#EEE"
            self.text              = "white"
            self.text_details      = "white"
            self.text_invert       = "#222"
            self.text_warn         = "orange"
            self.text_error        = "red"
            self.text_notice       = "cyan"
            self.crosshair         = "#303030"
            self.pinstripe         = "#303030" 
            self.entry_background  = "white" 
            self.slider_trough     = "#292b2f"
            self.main_line         = "#3c4048"
            self.highlight_line    = "cyan"  # #6b92a7
            self.ghost_line        = "#383c49"
            self.ghost_line_blue   = "#375772"
            self.guess             = "red"
            self.line_width        = 1
            self.dash_type         = (1, 5)
            self.text_size_small   = 10
            self.text_size_medium  = 12
            self.text_size_large   = 14
            self.text_size_xlarge  = 17
            self.data_font         = "Courier New"
            self.mnslac_logo       = "./icon-small.png"
        else:
            self.background        = "#fff"
            self.background_accent = "#222"
            self.background_dialog = "#EEE"
            self.text              = "black"
            self.text_details      = "white"
            self.text_invert       = "#222"
            self.text_warn         = "orange"
            self.text_error        = "red"
            self.text_notice       = "cyan"
            self.crosshair         = "#999"
            self.pinstripe         = "#303030" 
            self.entry_background  = "white" 
            self.slider_trough     = "#292b2f"  # "#292b2f"
            self.main_line         = "cyan"  # "#3c4048"
            self.highlight_line    = "green"  # "#6b92a7"
            self.ghost_line        = "red"  # "#383c49"
            self.ghost_line_blue   = ""  # "#375772"
            self.guess             = "red"
            self.line_width        = 4
            self.dash_type         = (3, 3)
            self.text_size_small   = 10
            self.text_size_medium  = 12
            self.text_size_large   = 14
            self.text_size_xlarge  = 17
            self.data_font         = "Courier New Bold"
            self.mnslac_logo       = "./icon-small-dark.png"

        self.orange            = "orange"
        self.yellow            = "yellow"
        self.red               = "red"
        self.cyan              = "cyan"
        self.white             = "white"
        self.purple            = "purple"
        self.blank             = ""
        
        EngColors.INSTANCE = self

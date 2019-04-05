class FakeMain:
    def __init__(self, src, multi_pipe=None):
        print("Init!")
        self.multi_pipe = multi_pipe
        self.src = src
        # if self.multi_pipe is None:
        #     run()
        
    def run(self):
        if self.multi_pipe is not None:
            self.multi_pipe.send("Test!")
        
        # Do all the other stuff here...


if __name__ == "__main__":
    src = "blah"
    m = FakeMain(src)
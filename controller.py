import glfw
import glfw.GLFW as GLFW_CONSTANTS
import numpy as np

from view import *

class App:
    """ The main program """


    def __init__(self, screenWidth, screenHeight):
        """ Set up the program """

        self.screenWidth = screenWidth
        self.screenHeight = screenHeight

        self.set_up_glfw()

        self.make_objects()

        self.set_up_input_systems()

        self.set_up_timer()

        self.mainLoop()
    
    def set_up_glfw(self) -> None:
        """ Set up the glfw environment """

        glfw.init()
        glfw.window_hint(GLFW_CONSTANTS.GLFW_CONTEXT_VERSION_MAJOR,3)
        glfw.window_hint(GLFW_CONSTANTS.GLFW_CONTEXT_VERSION_MINOR,3)
        glfw.window_hint(
            GLFW_CONSTANTS.GLFW_OPENGL_PROFILE, 
            GLFW_CONSTANTS.GLFW_OPENGL_CORE_PROFILE
        )
        glfw.window_hint(
            GLFW_CONSTANTS.GLFW_OPENGL_FORWARD_COMPAT, 
            GLFW_CONSTANTS.GLFW_TRUE
        )
        glfw.window_hint(GLFW_CONSTANTS.GLFW_DOUBLEBUFFER, False)
        self.window = glfw.create_window(
            self.screenWidth, self.screenHeight, "Title", None, None
        )
        glfw.make_context_current(self.window)

    def make_objects(self) -> None:
        """ Make any object used by the App"""

        self.renderer = Renderer(
            self.screenWidth, self.screenHeight, self.window
        )
        self.scene = Scene()
    
    def set_up_input_systems(self) -> None:
        """ Run any mouse/keyboard configuration here. """

        glfw.set_input_mode(
            self.window, 
            GLFW_CONSTANTS.GLFW_CURSOR, 
            GLFW_CONSTANTS.GLFW_CURSOR_HIDDEN
        )
        glfw.set_cursor_pos(
            self.window,
            self.screenWidth // 2, 
            self.screenHeight // 2
        )

        self.walk_offset_lookup = {
            1: 0,
            2: 90,
            3: 45,
            4: 180,
            6: 135,
            7: 90,
            8: 270,
            9: 315,
            11: 0,
            12: 225,
            13: 270,
            14: 180
        }
    
    def set_up_timer(self) -> None:
        """
            Set up the variables needed to measure the framerate
        """
        self.lastTime = glfw.get_time()
        self.currentTime = 0
        self.numFrames = 0
        self.frameTime = 0
    
    def mainLoop(self) -> None:
        """ Run the App """

        running = True
        while (running):

            #check events
            if glfw.window_should_close(self.window) \
                or glfw.get_key(self.window, GLFW_CONSTANTS.GLFW_KEY_ESCAPE) == GLFW_CONSTANTS.GLFW_PRESS:
                running = False
            
            self.handleKeys()
            self.handleMouse()

            glfw.poll_events()

            #update scene
            self.scene.update(self.frameTime / 16.667)
            
            self.renderer.render(
                camera = self.scene.camera,
                renderables = self.scene.renderables
            )

            #timing
            self.calcuateFramerate()

        self.quit()

    def handleKeys(self) -> None:
        """
            Handle keys.
        """

        combo = 0
        directionModifier = 0

        if glfw.get_key(
            self.window, GLFW_CONSTANTS.GLFW_KEY_W
            ) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 1
        elif glfw.get_key(
            self.window, GLFW_CONSTANTS.GLFW_KEY_A
            ) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 2
        elif glfw.get_key(
            self.window, GLFW_CONSTANTS.GLFW_KEY_S
            ) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 4
        elif glfw.get_key(
            self.window, GLFW_CONSTANTS.GLFW_KEY_D
            ) == GLFW_CONSTANTS.GLFW_PRESS:
            combo += 8
        
        if combo in self.walk_offset_lookup:

            directionModifier = self.walk_offset_lookup[combo]
            
            dPos = 0.1 * np.array(
                [
                    np.cos(np.deg2rad(self.scene.camera.eulers[2] + directionModifier)),
                    np.sin(np.deg2rad(self.scene.camera.eulers[2] + directionModifier)),
                    0
                ],
                dtype = np.float32
            )

            self.scene.move_camera(dPos)

    def handleMouse(self) -> None:
        """
            Handle mouse movement.
        """

        (x,y) = glfw.get_cursor_pos(self.window)
        rate = self.frameTime / 16.667
        theta_increment = rate * ((self.screenWidth / 2.0) - x)
        phi_increment = rate * ((self.screenHeight / 2.0) - y)
        dEulers = np.array([0, phi_increment, theta_increment], dtype=np.float32)
        self.scene.spin_camera(dEulers)
        glfw.set_cursor_pos(self.window, self.screenWidth // 2, self.screenHeight // 2)

    def calcuateFramerate(self) -> None:
        """
            Calculate the framerate and frametime
        """

        self.currentTime = glfw.get_time()
        delta = self.currentTime - self.lastTime
        if (delta >= 1):
            framerate = int(self.numFrames/delta)
            glfw.set_window_title(self.window, f"Running at {framerate} fps.")
            self.lastTime = self.currentTime
            self.numFrames = -1
            self.frameTime = float(1000.0 / max(60,framerate))
        self.numFrames += 1
    
    def quit(self):
        
        self.renderer.destroy()
        glfw.terminate()
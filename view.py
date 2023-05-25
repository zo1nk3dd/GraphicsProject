import glfw
from PIL import Image, ImageOps

from constants import *
from helper import *
from model import *

class Renderer:


    def __init__(
        self, 
        screenWidth: int, screenHeight: int,
        window):

        self.screenWidth = screenWidth
        self.screenHeight = screenHeight

        self.set_up_opengl(window)
        
        self.make_assets()

        self.set_onetime_uniforms()

        self.get_uniform_locations()
    
    def set_up_opengl(self, window) -> None:
        """
            Set up any general options used in OpenGL rendering.
        """

        glClearColor(0.0, 0.0, 0.0, 1)

        (w,h) = glfw.get_framebuffer_size(window)
        glViewport(0,0,w, h)

        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def make_assets(self) -> None:
        """
            Load/Create assets (eg. meshes and materials) that 
            the renderer will use.
        """

        self.meshes: dict[int, Mesh] = {
            OBJECT_LEAF: InstancedObjMesh("models/leaf.obj"),
            OBJECT_BRANCH: InstancedObjMesh("models/branch.obj"),
            OBJECT_CUBE: ObjMesh("models/cube.obj"),
            OBJECT_SKY: Quad2D(
                center = (0,0),
                size = (1,1)
            )
        }

        self.materials: dict[int, Material] = {
            OBJECT_LEAF: Material2D("gfx/leaf.jpeg"),
            OBJECT_BRANCH: Material2D("gfx/wood.jpeg"),
            OBJECT_CUBE: Material2D("gfx/wood.jpeg"),
            OBJECT_SKY: MaterialCubemap("gfx/sky")
        }

        self.shaders: dict[int, int] = {
            PIPELINE_SKY: createShader(
                "shaders/vertex_sky.txt", 
                "shaders/fragment_sky.txt"
            ),
            PIPELINE_3D: createShader(
                "shaders/vertex.txt", 
                "shaders/fragment.txt"
            )
        }

    def set_onetime_uniforms(self) -> None:
        """ Set any uniforms which can simply get set once and forgotten """
        
        glUseProgram(self.shaders[PIPELINE_3D])
        projection_transform = pyrr.matrix44.create_perspective_projection(
            fovy = 45, aspect = self.screenWidth / self.screenHeight, 
            near = 0.1, far = 50, dtype = np.float32
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shaders[PIPELINE_3D], "projection"), 
            1, GL_FALSE, projection_transform
        )
        glUniform1i(
            glGetUniformLocation(self.shaders[PIPELINE_3D], "imageTexture"), 1)
        glUniform1i(
            glGetUniformLocation(self.shaders[PIPELINE_3D], "skyTexture"), 0)
        
        glUseProgram(self.shaders[PIPELINE_SKY])
        glUniform1i(
            glGetUniformLocation(self.shaders[PIPELINE_SKY], "imageTexture"), 0)
    
    def get_uniform_locations(self) -> None:
        """ 
            Query and store the locations of any uniforms 
            on the shader 
        """

        glUseProgram(self.shaders[PIPELINE_SKY])
        self.cameraForwardsLocation = glGetUniformLocation(
            self.shaders[PIPELINE_SKY], "camera_forwards")
        self.cameraRightLocation = glGetUniformLocation(
            self.shaders[PIPELINE_SKY], "camera_right")
        self.cameraUpLocation = glGetUniformLocation(
            self.shaders[PIPELINE_SKY], "camera_up")

        glUseProgram(self.shaders[PIPELINE_3D])
        self.modelMatrixLocation = glGetUniformLocation(
            self.shaders[PIPELINE_3D], "model")
        self.viewMatrixLocation = glGetUniformLocation(
            self.shaders[PIPELINE_3D], "view")
        self.cameraPosLocation = glGetUniformLocation(
            self.shaders[PIPELINE_3D], "viewerPos")
    
    def render(
        self, camera: Player, 
        renderables: dict[int, list[Entity]]) -> None:
        """
            Render a frame.

            Parameters:

                camera: the camera to render from

                renderables: a dictionary of entities to draw, keys are the
                            entity types, for each of these there is a list
                            of entities.
        """

        #refresh screen
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        #draw sky
        glUseProgram(self.shaders[PIPELINE_SKY])
        glDisable(GL_DEPTH_TEST)
        self.materials[OBJECT_SKY].use()
        glUniform3fv(
            self.cameraForwardsLocation, 1, camera.forwards)
        glUniform3fv(
            self.cameraRightLocation, 1, camera.right)
        glUniform3fv(
            self.cameraUpLocation, 1, 
            (self.screenHeight / self.screenWidth) * camera.up)
        glBindVertexArray(self.meshes[OBJECT_SKY].vao)
        glDrawArrays(
            GL_TRIANGLES, 
            0, self.meshes[OBJECT_SKY].vertex_count)
        
        #Everything else
        glUseProgram(self.shaders[PIPELINE_3D])
        glEnable(GL_DEPTH_TEST)

        glUniformMatrix4fv(
            self.viewMatrixLocation, 
            1, GL_FALSE, camera.get_view_transform()
        )
        glUniform3fv(self.cameraPosLocation, 1, camera.position)
        self.materials[OBJECT_SKY].use()

        for objectType,objectList in renderables.items():
            mesh = self.meshes[objectType]
            material = self.materials[objectType]
            glBindVertexArray(mesh.vao)
            material.use()
            transforms = []
            for object in objectList:
                transforms.append(object.get_model_transform())
            mesh.send_instance_data(np.array(transforms, dtype=np.float32))
           
            glBindVertexArray(mesh.vao)
            glDrawArraysInstanced(GL_TRIANGLES, 0, mesh.vertex_count, len(transforms))

        glFlush()

    def destroy(self) -> None:
        """ Free any allocated memory """

        for (_,mesh) in self.meshes.items():
            mesh.destroy()
        for (_,material) in self.materials.items():
            material.destroy()
        for (_, shader) in self.shaders.items():
            glDeleteProgram(shader)

class Mesh:
    """ A general mesh """


    def __init__(self):

        self.vertex_count = 0

        self.vao = glGenVertexArrays(1)
        self.vbo = glGenBuffers(1)
    
    def destroy(self):
        
        glDeleteVertexArrays(1, (self.vao,))
        glDeleteBuffers(1,(self.vbo,))

class ObjMesh(Mesh):


    def __init__(self, filename):

        super().__init__()

        # x, y, z, s, t, nx, ny, nz
        vertices = load_model_from_file(filename)
        self.vertex_count = len(vertices)//8
        vertices = np.array(vertices, dtype=np.float32)
        
        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        #position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(0))
        #texture
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(12))
        #normal
        glEnableVertexAttribArray(2)
        glVertexAttribPointer(2, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(20))


class InstancedObjMesh(ObjMesh):

    def __init__(self, filename):
        super().__init__(filename)

        self.vbo_instance = glGenBuffers(1)

    def send_instance_data(self, data):
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo_instance)
        glBufferData(GL_ARRAY_BUFFER, data.nbytes, data, GL_STATIC_DRAW)

        glBindVertexArray(self.vao)
        # Instances
        glEnableVertexAttribArray(3)
        glVertexAttribPointer(3, 4, GL_FLOAT, GL_FALSE, 64, ctypes.c_void_p(0))
        glEnableVertexAttribArray(4)
        glVertexAttribPointer(4, 4, GL_FLOAT, GL_FALSE, 64, ctypes.c_void_p(16))
        glEnableVertexAttribArray(5)
        glVertexAttribPointer(5, 4, GL_FLOAT, GL_FALSE, 64, ctypes.c_void_p(32))
        glEnableVertexAttribArray(6)
        glVertexAttribPointer(6, 4, GL_FLOAT, GL_FALSE, 64, ctypes.c_void_p(48))

        glVertexAttribDivisor(3, 1)
        glVertexAttribDivisor(4, 1)
        glVertexAttribDivisor(5, 1)
        glVertexAttribDivisor(6, 1)

        glBindVertexArray(0)

class Quad2D(Mesh):


    def __init__(self, center: tuple[float], size: tuple[float]):

        super().__init__()

        # x, y
        x,y = center
        w,h = size
        vertices = (
            x + w, y - h,
            x - w, y - h,
            x - w, y + h,
            
            x - w, y + h,
            x + w, y + h,
            x + w, y - h,
        )
        self.vertex_count = 6
        vertices = np.array(vertices, dtype=np.float32)

        glBindVertexArray(self.vao)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
        #position
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 8, ctypes.c_void_p(0))

class Material:

    def __init__(self, textureType: int, textureUnit: int):
        self.texture = glGenTextures(1)
        self.textureType = textureType
        self.textureUnit = textureUnit
        glBindTexture(textureType, self.texture)
    
    def use(self):
        glActiveTexture(GL_TEXTURE0 + self.textureUnit)
        glBindTexture(self.textureType, self.texture)
    
    def destroy(self):
        glDeleteTextures(1, (self.texture,))

class Material2D(Material):

    
    def __init__(self, filepath):
        
        super().__init__(GL_TEXTURE_2D, 1)
        
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        with Image.open(filepath, mode = "r") as image:
            image_width,image_height = image.size
            image = image.convert("RGBA")
            img_data = bytes(image.tobytes())
            glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)
        glGenerateMipmap(GL_TEXTURE_2D)

class MaterialCubemap(Material):


    def __init__(self, filepath):

        super().__init__(GL_TEXTURE_CUBE_MAP, 0)

        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        #load textures
        with Image.open(f"{filepath}_left.png", mode = "r") as img:
            image_width,image_height = img.size
            img = img.convert('RGBA')
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_CUBE_MAP_NEGATIVE_Y,0,GL_RGBA8,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)
        
        with Image.open(f"{filepath}_right.png", mode = "r") as img:
            image_width,image_height = img.size
            img = ImageOps.flip(img)
            img = ImageOps.mirror(img)
            img = img.convert('RGBA')
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_Y,0,GL_RGBA8,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)
        
        with Image.open(f"{filepath}_top.png", mode = "r") as img:
            image_width,image_height = img.size
            img = img.rotate(90)
            img = img.convert('RGBA')
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_Z,0,GL_RGBA8,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)

        with Image.open(f"{filepath}_bottom.png", mode = "r") as img:
            image_width,image_height = img.size
            img = img.convert('RGBA')
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_CUBE_MAP_NEGATIVE_Z,0,GL_RGBA8,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)
        
        with Image.open(f"{filepath}_back.png", mode = "r") as img:
            image_width,image_height = img.size
            img = img.rotate(-90)
            img = img.convert('RGBA')
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_CUBE_MAP_NEGATIVE_X,0,GL_RGBA8,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)

        with Image.open(f"{filepath}_front.png", mode = "r") as img:
            image_width,image_height = img.size
            img = img.rotate(90)
            img = img.convert('RGBA')
            img_data = bytes(img.tobytes())
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X,0,GL_RGBA8,image_width,image_height,0,GL_RGBA,GL_UNSIGNED_BYTE,img_data)

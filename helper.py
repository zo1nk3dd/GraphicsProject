from OpenGL.GL import *
from OpenGL.GL.shaders import compileProgram,compileShader

def createShader(vertexFilepath: str, fragmentFilepath: str) -> int:
    """
        Compile and link a shader program from source.

        Parameters:

            vertexFilepath: filepath to the vertex shader source code (relative to this file)

            fragmentFilepath: filepath to the fragment shader source code (relative to this file)
        
        Returns:

            An integer, being a handle to the shader location on the graphics card
    """

    with open(vertexFilepath,'r') as f:
        vertex_src = f.readlines()

    with open(fragmentFilepath,'r') as f:
        fragment_src = f.readlines()
    
    shader = compileProgram(compileShader(vertex_src, GL_VERTEX_SHADER),
                            compileShader(fragment_src, GL_FRAGMENT_SHADER),
                            validate = False
                        )
    
    return shader

def load_model_from_file(
    filename: str) -> list[float]:
    """ 
        Read the given obj file and return a list of all the
        vertex data.
    """

    v = []
    vt = []
    vn = []
    vertices = []

    with open(filename,'r') as f:
        line = f.readline()
        while line:
            words = line.split(" ")
            if words[0] == "v":
                v.append(read_vertex_data(words))
            elif words[0] == "vt":
                vt.append(read_texcoord_data(words))
            elif words[0] == "vn":
                vn.append(read_normal_data(words))
            elif words[0] == "f":
                read_face_data(words, v, vt, vn, vertices)
            line = f.readline()
    
    return vertices

def read_vertex_data(words: list[str]) -> list[float]:
    """ 
        read the given position description and
        return the vertex it represents.
    """

    return [
        float(words[1]),
        float(words[2]),
        float(words[3])
    ]

def read_texcoord_data(words: list[str]) -> list[float]:
    """ 
        read the given texcoord description and
        return the texcoord it represents.
    """

    return [
        float(words[1]),
        float(words[2])
    ]

def read_normal_data(words: list[str]) -> list[float]:
    """ 
        read the given normal description and
        return the normal it represents.
    """

    return [
        float(words[1]),
        float(words[2]),
        float(words[3])
    ]

def read_face_data(
    words: list[str], 
    v: list[float], vt: list[float], vn: list[float], 
    vertices: list[float]) -> None:
    """
        Read the given face description, and use the
        data from the pre-filled v, vt, vn arrays to add
        data to the vertices array
    """
    
    triangles_in_face = len(words) - 3

    for i in range(triangles_in_face):
        read_corner(words[1], v, vt, vn, vertices)
        read_corner(words[i + 2], v, vt, vn, vertices)
        read_corner(words[i + 3], v, vt, vn, vertices)

def read_corner(
    description: str, 
    v: list[float], vt: list[float], vn: list[float], 
    vertices: list[float]) -> None:
    """
        Read the given corner description, then send the
        approprate v, vt, vn data to the vertices array.
    """

    v_vt_vn = description.split("/")

    for x in v[int(v_vt_vn[0]) - 1]:
        vertices.append(x)
    for x in vt[int(v_vt_vn[1]) - 1]:
        vertices.append(x)
    for x in vn[int(v_vt_vn[2]) - 1]:
        vertices.append(x)
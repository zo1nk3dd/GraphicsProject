import numpy as np
import pyrr
import random
from constants import *

class Event:

    def __init__(self, type, data):
        self.type = type
        self.data = data

class Entity:
    """ Represents a general object with a position and rotation applied"""


    def __init__(
        self, position: list[float], 
        eulers: list[float], objectType: int):
        """
            Initialize the entity, store its state and update its transform.

            Parameters:

                position: The position of the entity in the world (x,y,z)

                eulers: Angles (in degrees) representing rotations around the x,y,z axes.

                objectType: The type of object which the entity represents,
                            this should match a named constant.

        """

        self.position = np.array(position, dtype=np.float32)
        self.eulers = np.array(eulers, dtype=np.float32)
        self.objectType = objectType
    
    def get_model_transform(self) -> np.ndarray:
        """
            Calculates and returns the entity's transform matrix,
            based on its position and rotation.
        """

        model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
        
        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_x_rotation(
                theta = np.radians(self.eulers[0]), 
                dtype=np.float32
            )
        )

        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_y_rotation(
                theta = np.radians(self.eulers[1]), 
                dtype=np.float32
            )
        )

        model_transform = pyrr.matrix44.multiply(
            m1=model_transform, 
            m2=pyrr.matrix44.create_from_z_rotation(
                theta = np.radians(self.eulers[2]), 
                dtype=np.float32
            )
        )

        model_transform = pyrr.matrix44.multiply(
            m1=model_transform,
            m2=pyrr.matrix44.create_from_translation(
                vec=self.position,
                dtype=np.float32
            )
        )

        return model_transform

    def update(self, rate: float) -> Event:

        raise NotImplementedError
    
class Cube(Entity):


    def __init__(
        self, position: list[float], 
        eulers: list[float]):

        super().__init__(position, eulers, OBJECT_CUBE)
    
    def update(self, rate: float) -> None:
        return None
        # self.eulers[1] += 0.25 * rate
        # if self.eulers[1] > 360:
        #     self.eulers[1] -= 360

class Leaf(Entity):

    def __init__(self, position: list[float], eulers: list[float], branch):
        super().__init__(position, eulers, OBJECT_LEAF)
        self.branch = branch
        self.age = 1

    def update(self, rate):
        return None

    def get_model_transform(self):
        # TODO leaf growing
        scale_factor = 1
        scale_transform = pyrr.matrix44.create_from_scale([scale_factor, scale_factor, scale_factor])
        mt = scale_transform @ super().get_model_transform() @ self.branch.get_model_transform()
        return mt
        


class Branch(Entity):

    def __init__(self, position: list[float], eulers: list[float], parent):
        super().__init__(position, eulers, OBJECT_BRANCH)

        self.radius = 1
        self.height = 4
        self.parent = parent
        self.child = None
        self.leaves = []

        self.age = 0

    def calculate_leaf_pos(self):
        theta = 360 * random.randint(0, 19) / 20 # Random angle on the branch to place the leaf
        branch_space_position = [
            self.position[0] + 0.8 * np.sin(np.radians(theta)), 
            self.position[1] + 0.8 * np.cos(np.radians(theta)), 
            self.position[2] + 4
        ]

        eulers = [
            self.eulers[0],
            self.eulers[1],
            self.eulers[2] + theta
        ]

        return branch_space_position, eulers

    def grow_leaf(self):
        vertex_pos, eulers = self.calculate_leaf_pos()
        self.leaves.append(Leaf(vertex_pos, eulers, self))

    def grow_wider(self, delta: float):
        self.radius += delta

    def grow_taller(self, delta: float):
        self.height += delta

    def update(self, rate):
        self.age += 1
        if self.age % 100 == 0:
            self.grow_taller(0.01)
            return None
        elif self.age % 200 == 1:
            # self.grow_wider(0.01)
            return None
        elif self.age % 300 == 1 and len(self.leaves) < 4:
            self.grow_leaf()
            return Event(EVENT_NEW, self.leaves[-1])

    def get_model_transform(self):
        return pyrr.matrix44.create_from_scale([self.radius, self.radius, self.height / 4.0]) @ super().get_model_transform()

class Player(Entity):
    """ A first person camera controller. """


    def __init__(self, position: list[float], eulers: list[float]):

        super().__init__(position, eulers, OBJECT_CAMERA)

        self.localUp = np.array([0,0,1], dtype=np.float32)

        #directions after rotation
        self.up = np.array([0,0,1], dtype=np.float32)
        self.right = np.array([0,1,0], dtype=np.float32)
        self.forwards = np.array([1,0,0], dtype=np.float32)
    
    def calculate_vectors(self) -> None:
        """ 
            Calculate the camera's fundamental vectors.

            There are various ways to do this, this function
            achieves it by using cross products to produce
            an orthonormal basis.
        """

        #calculate the forwards vector directly using spherical coordinates
        self.forwards = np.array(
            [
                np.cos(np.radians(self.eulers[2])) * np.cos(np.radians(self.eulers[1])),
                np.sin(np.radians(self.eulers[2])) * np.cos(np.radians(self.eulers[1])),
                np.sin(np.radians(self.eulers[1]))
            ],
            dtype=np.float32
        )
        self.right = pyrr.vector.normalise(np.cross(self.forwards, self.localUp))
        self.up = pyrr.vector.normalise(np.cross(self.right, self.forwards))

    def update(self) -> None:
        """ Updates the camera """

        self.calculate_vectors()

    def get_view_transform(self) -> np.ndarray:
        """ Return's the camera's view transform. """

        return pyrr.matrix44.create_look_at(
            eye = self.position,
            target = self.position + self.forwards,
            up = self.up,
            dtype = np.float32
        )

class Scene:
    """ 
        Manages all logical objects in the game,
        and their interactions.
    """


    def __init__(self):
        """ Create a scene """

        self.renderables: dict[int,list[Entity]] = {}
        self.renderables[OBJECT_BRANCH] = [
            Branch(
                position=[0,0,0],
                eulers=[10,0,0],
                parent=None
            )
        ]

        self.camera = Player(
            position = [-10,0,4],
            eulers = [0,0,0]
        )

    def update(self, rate: float) -> None:
        """ 
            Update all objects managed by the scene.

            Parameters:

                rate: framerate correction factor
        """
        events = []
        for _,objectList in self.renderables.items():
            for object in objectList:
                event = object.update(rate)
                if event:
                    events.append(event)

        for event in events:
            if event.type == EVENT_NEW:
                entity = event.data
                
                if entity.objectType in self.renderables:
                    self.renderables[entity.objectType].append(entity)
                else:
                    self.renderables[entity.objectType] = [entity]
        
        self.camera.update()

    def move_camera(self, dPos: np.ndarray) -> None:
        """ Moves the camera by the given amount """

        self.camera.position += dPos
    
    def spin_camera(self, dEulers: np.ndarray) -> None:
        """ 
            Change the camera's euler angles by the given amount,
            performing appropriate bounds checks.
        """

        self.camera.eulers += dEulers

        if self.camera.eulers[2] < 0:
            self.camera.eulers[2] += 360
        elif self.camera.eulers[2] > 360:
            self.camera.eulers[2] -= 360
        
        self.camera.eulers[1] = min(89, max(-89, self.camera.eulers[1]))
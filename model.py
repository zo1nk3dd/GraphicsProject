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
        self.dying = False

    def fall_off(self):
        self.dying = True

    def update(self, rate):
        if not self.dying:
            self.age += 1
        else:
            self.age -= 1
            if self.age == 0:
                return Event(EVENT_DEL, self)

    def get_model_transform(self):
        # TODO leaf growing
        scale_factor = min(0.2, self.age / 1000)
        scale_transform = pyrr.matrix44.create_from_scale([scale_factor, scale_factor, scale_factor])
        return scale_transform @ super().get_model_transform() 
        
class Branch(Entity):

    def __init__(self, position: list[float], eulers: list[float], parent=None, radius=1, height=1):
        super().__init__(position, eulers, OBJECT_BRANCH)

        self.radius = radius
        self.height = height
        self.parent = parent
        self.above = None
        self.split = None
        self.leaves = []

        self.age = 0
        self.depth = self.parent.depth + 1 if self.parent else 1

    def calculate_leaf_pos(self):
        theta = 360 * random.randint(0, 19) / 20 # Random angle on the branch to place the leaf
        
        base = np.array([
            BRANCH_TOP_RADIUS * np.sin(np.radians(theta)), 
            BRANCH_TOP_RADIUS * np.cos(np.radians(theta)), 
            BRANCH_HEIGHT,
            1
        ]).reshape(1, 4)


        new_base = base @ self.get_model_transform()
        branch_space_position = [
            new_base[0,0],
            new_base[0,1],
            new_base[0,2]
        ]

        eulers = [
            self.eulers[0],
            self.eulers[1],
            self.eulers[2] + theta
        ]

        return branch_space_position, eulers
    
    def calculate_extend_pos(self):
        center_top = np.array([
            0,
            0,
            BRANCH_HEIGHT,
            1
        ]).reshape(1, 4)


        new_base = center_top @ self.get_model_transform()
        branch_space_position = [
            new_base[0,0],
            new_base[0,1],
            new_base[0,2]
        ]

        eulers = [
            self.eulers[0],
            self.eulers[1],
            self.eulers[2]
        ]

        return branch_space_position, eulers
    
    def calculate_split_pos(self):
        split_pos = np.array([
            0,
            BRANCH_SPLIT_Y * self.radius,
            BRANCH_SPLIT_Z * self.height,
            1
        ]).reshape(1, 4)


        new_base = split_pos @ self.get_model_transform()
        branch_space_position = [
            new_base[0,0],
            new_base[0,1],
            new_base[0,2]
        ]
        rotation = random.randint(0, 20) * 18
        eulers = [
            self.eulers[0] + BRANCH_SPLIT_X_ROTATION,
            self.eulers[1],
            self.eulers[2] + rotation
        ]

        return branch_space_position, eulers

    def grow_leaf(self):
        vertex_pos, eulers = self.calculate_leaf_pos()
        self.leaves.append(Leaf(vertex_pos, eulers, self))

    def grow_branch(self):
        vertex_pos, eulers = self.calculate_extend_pos()
        self.above = Branch(vertex_pos, eulers, parent=self, radius = 0, height=0)

    def split_branch(self):
        vertex_pos, eulers = self.calculate_split_pos()
        self.split = Branch(vertex_pos, eulers, parent=self, radius=0, height=0)

    def attempt_split(self):
        if self.split == None:
            if self.depth < MAX_DEPTH and random.random() < self.depth / 10:
                self.split_branch()
                return True
            else:
                self.split = -1
        elif self.split == -1:
            if self.depth > MAX_DEPTH * 0.75:
                self.split = None
        return False
        

    def attempt_extend(self):
        if self.height < 1:
            self.height += 0.001
        elif self.above == None and self.radius > MIN_EXTEND_RADIUS and self.depth < MAX_DEPTH:
            self.height = 1
            self.grow_branch()
            return True
        
        return False
    
    def attempt_grow_leaf(self):
        if self.radius < LEAF_GROWING_MAX_RADIUS and len(self.leaves) < (1 / self.radius) and self.above:
            self.grow_leaf()
            return True
        return False

    def attempt_grow_wider(self):
        if self.parent == None:
            # base of tree
            self.radius += 0.00001
        if self.radius > LEAF_GROWING_MAX_RADIUS and len(self.leaves) != 0:
            self.leaves.pop().fall_off()
        if self.split != None and self.split != -1:
            self.split.radius = self.radius * BRANCH_SPLIT_RADIUS
        if self.above != None:
            self.above.radius = self.radius * BRANCH_TOP_RADIUS

    
    def update(self, rate):
        self.attempt_grow_wider()

        if self.attempt_extend():
            return Event(EVENT_NEW, self.above)
        
        # If radius is large, no branching. Small radius, high branching
        if self.attempt_split():
            return Event(EVENT_NEW, self.split)

        if self.attempt_grow_leaf():
            return Event(EVENT_NEW, self.leaves[-1])

        
    def get_model_transform(self):
        return pyrr.matrix44.create_from_scale([self.radius, self.radius, self.height]) @ super().get_model_transform()
        
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
                eulers=[0,0,0],
                radius = 0.1
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
            if event.type == EVENT_DEL:
                entity = event.data
                self.renderables[entity.objectType].remove(entity)
        
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
from random import choice
from ..settings import STATIC_URL

images = [
    (STATIC_URL + "img/CygnusA.jpg", "J. McKean & M. Wise"),
    (STATIC_URL + "img/LOFAR_Superterp.jpg", "")
]

def get_image():
    return choice(images)

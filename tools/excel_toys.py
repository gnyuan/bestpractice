'''
Excel里一些玩具函数
'''
import asyncio
import datetime as dt
import numpy as np
import cv2

import xloil as xlo


def render_frame(A: float, B: float, R1, R2, K1, K2, screen_size, theta_spacing, phi_spacing, illumination) -> np.ndarray:
    """
    Returns a frame of the spinning 3D donut.
    Based on the pseudocode from: https://www.a1k0n.net/2011/07/20/donut-math.html
    """
    cos_A = np.cos(A)
    sin_A = np.sin(A)
    cos_B = np.cos(B)
    sin_B = np.sin(B)

    output = np.full((screen_size, screen_size), " ")  # (40, 40)
    zbuffer = np.zeros((screen_size, screen_size))  # (40, 40)

    cos_phi = np.cos(phi := np.arange(0, 2 * np.pi, phi_spacing))  # (315,)
    sin_phi = np.sin(phi)  # (315,)
    cos_theta = np.cos(theta := np.arange(0, 2 * np.pi, theta_spacing))  # (90,)
    sin_theta = np.sin(theta)  # (90,)
    circle_x = R2 + R1 * cos_theta  # (90,)
    circle_y = R1 * sin_theta  # (90,)

    x = (np.outer(cos_B * cos_phi + sin_A * sin_B * sin_phi, circle_x) - circle_y * cos_A * sin_B).T  # (90, 315)
    y = (np.outer(sin_B * cos_phi - sin_A * cos_B * sin_phi, circle_x) + circle_y * cos_A * cos_B).T  # (90, 315)
    z = ((K2 + cos_A * np.outer(sin_phi, circle_x)) + circle_y * sin_A).T  # (90, 315)
    ooz = np.reciprocal(z)  # Calculates 1/z
    xp = (screen_size / 2 + K1 * ooz * x).astype(int)  # (90, 315)
    yp = (screen_size / 2 - K1 * ooz * y).astype(int)  # (90, 315)
    L1 = (((np.outer(cos_phi, cos_theta) * sin_B) - cos_A * np.outer(sin_phi, cos_theta)) - sin_A * sin_theta)  # (315, 90)
    L2 = cos_B * (cos_A * sin_theta - np.outer(sin_phi, cos_theta * sin_A))  # (315, 90)
    L = np.around(((L1 + L2) * 8)).astype(int).T  # (90, 315)
    mask_L = L >= 0  # (90, 315)
    chars = illumination[L]  # (90, 315)

    for i in range(90):
        mask = mask_L[i] & (ooz[i] > zbuffer[xp[i], yp[i]])  # (315,)

        zbuffer[xp[i], yp[i]] = np.where(mask, ooz[i], zbuffer[xp[i], yp[i]])
        output[xp[i], yp[i]] = np.where(mask, chars[i], output[xp[i], yp[i]])

    ret = np.copy(output)
    return ret


def pprint(array: np.ndarray) -> None:
    """Pretty print the frame."""
    print(*[" ".join(row) for row in array], sep="\n")


@xlo.func
async def donut():
    screen_size = 40
    theta_spacing = 0.07
    phi_spacing = 0.02
    illumination = np.fromiter(".,-~:;=!*#$@", dtype="<U1")

    A = 1
    B = 1
    R1 = 1
    R2 = 2
    K2 = 5
    K1 = screen_size * K2 * 3 / (8 * (R1 + R2))

    while True:
        A += theta_spacing
        B += phi_spacing
        yield render_frame(A, B, R1, R2, K1, K2, screen_size, theta_spacing, phi_spacing, illumination)
        await asyncio.sleep(0.0001)

@xlo.func
async def zNow():
    while True:
        yield dt.datetime.now()
        await asyncio.sleep(0.0001)


@xlo.func
def ascii_art():
    input=r'd:\down.jpg'
    char_list='ABCDEFGHIJKLMNOPQRSTVUWXYZ'
    num_cols=300

    char_list = list(char_list)
    scale = 2    

    num_chars = len(char_list)
    image = cv2.imread(input)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = image.shape
    cell_width = width / num_cols
    cell_height = scale * cell_width
    num_rows = int(height / cell_height)

    if num_cols > width or num_rows > height:
        print("Too many columns or rows. Use default setting")
        cell_width = 6
        cell_height = 12
        num_cols = int(width / cell_width)
        num_rows = int(height / cell_height)

    ascii_output = ""

    for i in range(num_rows):
        line = "".join([char_list[min(int(np.mean(image[int(i * cell_height):min(int((i + 1) * cell_height), height),
                                                  int(j * cell_width):min(int((j + 1) * cell_width),
                                                                          width)]) / 255 * num_chars), num_chars - 1)]
                        for j in range(num_cols)]) + "\n"
        ascii_output += line  # Add the line to the output string

    # Save the ASCII output to numpy
    ascii_array = np.full((num_rows, num_cols), '', dtype='<U1')  # Create an empty array to store characters
    
    for i in range(num_rows):
        for j in range(num_cols):
            # Extract the region of the image and calculate the average brightness
            cell_region = image[int(i * cell_height):min(int((i + 1) * cell_height), height),
                                int(j * cell_width):min(int((j + 1) * cell_width), width)]
            avg_brightness = np.mean(cell_region)  # Calculate average brightness of the region
            
            # Map the brightness to a character
            char_index = int(avg_brightness / 255 * len(char_list))  # Convert brightness to an index
            ascii_array[i, j] = char_list[min(char_index, len(char_list) - 1)]  # Store the character
    return ascii_array


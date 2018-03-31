import cv2
import numpy as np
import quad
import mouse
import utils

screen = mouse.screensize()
cap = cv2.VideoCapture(1)
screenCnt = None
k_thresh = 125 # adjust for lighting

# track when paper has stabilized
counter = 0
counter_thresh = 6
gap_counter = 0
gap_thresh = 3
bg_thresh = None
ppr_quad = None

# density represent grid of samples from paper area
density = [30, 30]
d_tot = density[0] * density[1]
ref_white = [128, 128, 128]
RED = (0, 0, 255)
GREEN = (0, 255, 0)
BLUE = (255, 0, 0)

# convert point from density coordinates to fractional coordinates
def dpt2fpt(p):
    x, y = p
    return ((x+1)/(density[0]+1), (y+1)/(density[1]+1))

# get average pixel color sampled over the paper
def get_white():
    ppr_img = ppr_quad.transform(img)
    out = np.array([0, 0, 0])
    for x in range(density[0]):
        for y in range(density[1]):
            p = (x,y)
            out += utils.get_pixel(ppr_img, dpt2fpt(p))
    return (out / d_tot).astype(int)

while(True):
    ret,img = cap.read()
    img = cv2.flip(img,1)
    img = cv2.flip(img,0)
    orig = img.copy()
    gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, k_thresh, 255, cv2.THRESH_BINARY)[1]
    edges = cv2.Canny(thresh, 50, 200)
    (_, contours, _) = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(contours, key = cv2.contourArea, reverse = True)[:10]

    # loop over our contours
    for c in cnts:
        # approximate the contour
        peri = cv2.arcLength(c, True)
        area = cv2.contourArea(c)
        approx = cv2.approxPolyDP(c, 0.01 * peri, True)
        # found paper
        if len(approx) == 4 and peri > 1500 and area > 50000:
            counter += 1
            gap_counter = 0
            if counter >= counter_thresh:
                counter = 0
                screenCnt = approx
                bg_thresh = np.zeros(thresh.shape, dtype=np.uint8)
                ppr_quad = quad.Quad(map(lambda x: x[0], screenCnt))
                ref_white = get_white()
                cv2.fillConvexPoly(bg_thresh, ppr_quad.points, 255)
                cv2.polylines(bg_thresh, [ppr_quad.points], True, 0, 5)
            break

    # allow for brief losses in tracking the paper
    gap_counter += 1
    if gap_counter >= gap_thresh:
        counter = 0

    # if paper is detected
    if bg_thresh is not None:
        ppr_img = ppr_quad.transform(img)
        utils.draw_box(ppr_img, (0,0), (1,1), GREEN)
        utils.draw_box(ppr_img, (0,0), (0.33,0.33), GREEN)
        utils.draw_box(ppr_img, (0.33,0), (0.66,0.33), GREEN)
        utils.draw_box(ppr_img, (0.66,0), (1,1), GREEN)

        # for x in range(int(density[0]/3)):
        #     for y in range(int(density[1]/3)):
        #         p = (x,y)
        #         if np.mean(utils.get_pixel(ppr_img, dpt2fpt(p))) > 100:
        #             utils.draw_point(ppr_img, dpt2fpt(p), BLUE)
        #         else:
        #             utils.draw_point(ppr_img, dpt2fpt(p), RED)

        # for x in range(density[0]):
        #     for y in range(density[1]):
        #         p = (x,y)
        #         utils.draw_point(ppr_img, dpt2fpt(p), BLUE)

        cv2.imshow('Frame', ppr_img)
    else:
        cv2.drawContours(img, cnts, -1, BLUE, 3)
        cv2.imshow('Frame', img)

    if cv2.waitKey(1) &0xFF == ord('q'):
        break

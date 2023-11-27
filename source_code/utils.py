import math
import re

import numpy as np
from scipy.signal import butter, lfilter, freqz
from sklearn.metrics import r2_score
from itertools import permutations
import pandas as pd


# f is the filename for bounding boxes
# d is the data csv


def detect_truncation(box_data, axis='y-axis', inverted=False):
    """
    Fuction takes in the axis specification data and identifies if the y-axis given is truncatedg
    return: True if truncated, False if not
    """

    df = pd.read_csv(box_data)
    df = df[['text', 'type', 'y']]  # drop all others, only need 'text', 'type' and the y-position
    df = df.loc[df['type'] == axis+'-label']
    # extract row with min to check of text contains zero
    y_label = df[df['y'] == df['y'].max()] if not inverted else df[df['y'] == df['y'].min()]
    y_label_text = y_label.iloc[0]['text']
    y_label_max = y_label.iloc[len(y_label)-1]['y']
    truncated = False
    # check if axis starts at zero and if axis crosses zero (chart is not truncated if it extends from -1 to +1)
    if (extract_float(y_label_text) != 0 ) and (np.sign(extract_float(y_label_text)) == np.sign(extract_float(y_label_max))):
        truncated = True

    return truncated


def detect_inverted_axis(box_data, axis='y-axis'):
    """
    Fuction takes in the axis specification data and identifies if the given y-axis is inverted
    return: True if inverted, False if not
    """
    df = pd.read_csv(box_data)
    df = df[['text', 'type', 'y']]  # drop all others, only need 'text', 'type' and the y-position
    df = df.loc[df['type'] == axis+'-label']
    # extract rows with min and max values and select their text
    top_y_label = df[df['y'] == df['y'].min()]
    top_y_label_text = top_y_label.iloc[0]['text']
    bottom_y_label = df[df['y'] == df['y'].max()]
    bottom_y_label_text = bottom_y_label.iloc[0]['text']
    inverted = False
    if extract_float(bottom_y_label_text) > extract_float(top_y_label_text):
        inverted = True

    return inverted


def detect_missing_labels(box_data):
    """
    Function takes in bounding box data and detects if there are any labels missing.
    Missing title, x-axis-title or y-axis-title will lead to those placed being marked in the recommended chart
    Missing legend-title or legend-labels will not be marked in the recommended chart
    Missing x-axis-labels or y-axis labels will result in us being unable to draw a recommended chart due to how the chart and axis data is stored
    """
    box_data = pd.read_csv(box_data)
    type_values = box_data['type'].values
    # as a chart can contain multiple axis, find all axis and add them to the list of possible types (both title and label for each axis)
    new_axis_labels = list(set(filter(lambda x: re.match('^[xy][0-9]+-axis-label$', x), type_values)))
    new_axis_labels.sort()
    # add title and label for each axis to the list of possible types
    new_axis = [f(value) for value in new_axis_labels for f in (lambda x: x[:-5]+'title', lambda x: x)]
    # we intentionally left out 'text-label' as that is optional
    # we also left out 'legend-title' and 'legend-label' as those are optional
    possible_types = ['title', 'x-axis-title', 'x-axis-label', 'y-axis-title', 'y-axis-label'] + new_axis # +['legend-title', 'legend-label'] 
    missing = list(filter(lambda type: type not in type_values, possible_types))
    # if there are any missing labels, return them, otherwise return False
    if missing != []:
        missing.insert(0, True) #insert true at the beginning of the list to indicate that there are missing labels
        return missing
    else:
        return [False]

def detect_inconsistent_axis_scales(box_data):
    """
    Function takes in bounding boxes and detects if one or more of the axis do not follow a linear scale
    returns a tuple of all detected inconsistencies (non-linear x-axis, non-linear y-axis, inconsistent tick labels on x-axis, incosistent tick labels on y-axis) each in form of a list of booleans describing which axis (x-axis, x1-axis, etc.) the inconsistency was detected in
    """
    box_data = pd.read_csv(box_data)
    
    # different_axis_frames is a list of the different dataframes of the different axis
    different_axis_frames = []
    for type in box_data['type'].unique():
        if re.match('^[xy][0-9]?-axis-label$', type):       # regex represents x/y-axis-labels as a chart might have multiple of each
            different_axis_frames.append(box_data[box_data['type'] == type])          

    nonLinearX = []
    nonLinearY = []
    inconsistentTicksX = []
    inconsistentTicksY = []

    different_axis_frames.sort(key=lambda x: x['type'].iloc[0]) # sort the axis dataframes by their type (x-axis-label, x1-axis-label, y0-axis-label, y1-axis-label, etc.)

    # for each axis check what inconsistencies exist
    for axis_frame in different_axis_frames:
        nonLinear, inconsistentTicks = check_axis_consistency(axis_frame)
        if axis_frame['type'].iloc[0][0] == 'x':    #if the first letter in the string is x, it is an x-axis
            nonLinearX.append(nonLinear)
            inconsistentTicksX.append(inconsistentTicks)
        else:
            nonLinearY.append(nonLinear)
            inconsistentTicksY.append(inconsistentTicks)

    return nonLinearX, nonLinearY, inconsistentTicksX, inconsistentTicksY

def check_axis_consistency(axis_data):
    """
    Takes in bounding boxes from axis lables of ONE axis and calculates whether the axis scale and/or the placement of labels is inconsistent for the axis
    returns a list of detected inconsistencies in axis scales and/or label placements
    """
    nonLinear = False
    inconsistentTicks = False
    axis_data = axis_data.copy()        #we need to make a copy of the dataframe to avoid a SettingWithCopyWarning
    axis_name = axis_data['type'].iloc[0]
    axis = 'y' if 'y' in axis_name else 'x'      #we assume all elements have the same type and only check for first element if it belongs to the x or y axis
    if axis == 'x':
        axis_data['midpoint'] = axis_data['x'] + axis_data['width']/2
    elif axis == 'y':
        axis_data['midpoint'] = axis_data['y'] + axis_data['height']/2
    else: 
        raise Exception("Somehow the axis is either a X-axis or a Y-axis")
    axis_data = axis_data.sort_values(by=['midpoint'])      #sort the dataframe by the midpoint of the bounding boxes to ensure they are in the correct order
    #print('midpoints: ', axis_data['midpoint'])
    distances_to_next_label = axis_data['midpoint'].diff(periods=-1).dropna()
    #print('distances_to_next_label', distances_to_next_label)

    # printing only for now, change it later to return useful information
    consistency_of_label_placements = calculate_conistency(distances_to_next_label, 0.10)
    if consistency_of_label_placements:
        print("The ticks across the "+axis_name+" are place consistently!")
    else:
        print("The ticks across the "+axis_name+" are place inconsistently!")
        inconsistentTicks = True

    numeric_texts = None
    try:
        # only calculate if distance between label values ist consistent, disregarding their physical placement on the axis, since we already checked that
        numeric_texts = axis_data['text'].apply(extract_float)
        value_difference_to_next_label = numeric_texts.diff(periods=-1).dropna()
        # distance_to_difference_factors = distances_to_next_label / value_difference_to_next_label
        # consistency_of_scale = calculate_conistency(distance_to_difference_factors, 0.05)
        consistency_of_scale = calculate_conistency(value_difference_to_next_label, 0.01)

        # printing only for now, change it later to return useful information
        if consistency_of_scale:
            print("The "+axis_name+" axis follows a linear scale!")
        else:
            print("The "+axis_name+" axis does not follow a linear scale!")
            nonLinear = True
    except ValueError: 
        print('cannot check axis scaling because not all labels contain numeric information!')

    # later for the returns: we need to find a way to draw the chart in an "unwarped" way, meaning we need the distances between the labels together with middlepoint of the labels and transform the corresponding x/y values to show them in a linear way
    return nonLinear, inconsistentTicks

def detect_multiple_axis(box_data):
    """
    Function takes in bounding boxes, detects if there are multiple axis and adjusts the types of the axis labels and titles in the csv file to represent these different axis.
    Returns a list containing true and all detected axis or containing False if only one x and one y axis were detected
    """
    result = [False]
    box_data = pd.read_csv(box_data)

    split_x_axis_labels = split_axis_labels(box_data[box_data['type'].str.contains('^x.*label$')], 'x')
    for x_axis_label in split_x_axis_labels:
        result.append(x_axis_label['type'].iloc[0].replace('-label', '')) 
    if len(split_x_axis_labels) > 1:
        result[0] = True
        
    split_y_axis_labels = split_axis_labels(box_data[box_data['type'].str.contains('^y.*label$')], 'y')
    for y_axis_label in split_y_axis_labels:
        result.append(y_axis_label['type'].iloc[0].replace('-label', ''))
    if len(split_y_axis_labels) > 1:
        result[0] = True


    # if there are multiple axis and titles then we need to map each title to the corresponding axis
    x_axis_titles = box_data[box_data['type'].str.contains('^x.*title$')].copy()
    if len(x_axis_titles) == 1 and len(split_x_axis_labels) == 1:
        x_axis_titles['type'] = split_x_axis_labels[0]['type'].iloc[0].replace('label', 'title')
        x_axis_titles.set_index('id', inplace=True)
        box_data.update(x_axis_titles)
    elif len(split_x_axis_labels) > 1: 
        mapped_x_axis = map_axis_titles_to_axis(x_axis_titles, split_x_axis_labels)
        # we have to concat, delete duplicates and sort again because the update function cannot add new rows
        box_data = pd.concat([box_data, mapped_x_axis]).drop_duplicates(subset=['id', 'x', 'y', 'width', 'height', 'text'], keep='last').sort_values(by=['id'])
        box_data = box_data.sort_values(by=['id'])
        
    y_axis_titles = box_data[box_data['type'].str.contains('^y.*title$')]
    if len(y_axis_titles) == 1 and len(split_y_axis_labels) == 1:
        y_axis_titles['type'] = split_y_axis_labels[0]['type'].iloc[0].replace('label', 'title')
        y_axis_titles.set_index('id', inplace=True)
        box_data.update(y_axis_titles)
    elif len(split_y_axis_labels) > 1:
        mapped_y_axis = map_axis_titles_to_axis(y_axis_titles, split_y_axis_labels)
        # we have to concat, delete duplicates and sort again because the update function cannot add new rows
        box_data = pd.concat([box_data, mapped_y_axis]).drop_duplicates(subset=['id', 'x', 'y', 'width', 'height', 'text'], keep='last')
        box_data = box_data.sort_values(by=['id'])

    # update the Bounding Box data with the new axis labels (first add x labels, then y labels)
    box_data.set_index('id', inplace=True)
    for x_axis_label in split_x_axis_labels:
        x_axis_label.set_index('id', inplace=True)
        box_data.update(x_axis_label)
    for y_axis_label in split_y_axis_labels:
        y_axis_label.set_index('id', inplace=True)
        box_data.update(y_axis_label)

    # create new temporary csv file to update axis types without affecting the original csv file
    box_data.to_csv('temp_box_data.csv')
    return result, 'temp_box_data.csv'

def map_axis_titles_to_axis(axis_titles, split_axis_labels):
    """
    Function takes in axis titles and axis labels and updates the titles type information to fit the corresponding axis
    returns the updated axis titles
    """
    # list to include the relevant box data for each axis in form of a dictionary
    axis_box_data_list = []
    for axis in split_axis_labels:
        x_min = axis['x'].min()
        y_min = axis['y'].min()
        x_max = (axis['x']+axis['width']).max()
        y_max = (axis['y']+axis['height']).max()
        # for each axis add a dictionary containing the axis name and all relevant points of the bounding box
        axis_box_data_list.append({'axis_name': axis['type'].iloc[0].replace('label', ''), 'x_min': x_min, 'y_min': y_min, 'x_max': x_max, 'y_max': y_max})

    # create a new dataframe, which includes the distances from every axis title to every axis
    titles_to_axis_distances = pd.DataFrame(columns=['axis_title', 'axis_name', 'distance'])
    for index, title in axis_titles.iterrows():
        for axis in axis_box_data_list:
            distance = min_distance((title['x'], title['y'], title['x']+title['width'], title['y']+title['height']), (axis['x_min'], axis['y_min'], axis['x_max'], axis['y_max']))
            titles_to_axis_distances = titles_to_axis_distances.append({'axis_title': index, 'axis_name': axis['axis_name'], 'distance': distance}, ignore_index=True)
        
    # it is possible that one axis label is closer to an axis that it does not belong to compared to the axis it would belong to. Then one axis title would be far away from the nearest still available axis
    # When we pair the axis titles with the axis, if the overall distance for the pairs is minimized, we ensure than all axis are mapped correctly
    # we solve this minimization problem by iterating over all permutations, so that every axis title gets 'priority to pick' the closest axis and we go through all possible combinations
    best_overall_distance = -1
    best_title_axis_pairs = []
    for series in permutations(axis_titles['id']):
        available_options = titles_to_axis_distances.copy()
        overall_distance = 0
        title_axis_pairs = []
        for elem in series:
            if len(available_options) == 0:
                break
            # get the distances for only the current title:
            current_title_distances = available_options[available_options['axis_title'] == elem]    
            # get the best distance for the current title from the still available options:
            best_distance = current_title_distances[current_title_distances['distance'] == current_title_distances['distance'].min()] 
            # remove all the distances to the chosen axis from the available options:
            available_options = available_options[available_options['axis_name'] != best_distance['axis_name'].iloc[0]] 
            overall_distance += best_distance['distance'].iloc[0]
            title_axis_pairs.append({'title': elem, 'axis': best_distance['axis_name'].iloc[0]})
        if best_overall_distance == -1 or overall_distance < best_overall_distance:
            best_overall_distance = overall_distance
            best_title_axis_pairs = title_axis_pairs

    # update the axis titles with the new axis information so that the csv file can be updated
    axis_titles = axis_titles.copy()        #we need to make a copy of the dataframe to avoid a SettingWithCopyWarning
    for pair in best_title_axis_pairs:
        axis_titles.loc[pair['title'], 'type'] = pair['axis'] + 'title'

    # if there are more titles than axis, then there has to be something wrong with the identification of the axis titles
    if len(axis_titles) > len(axis_box_data_list):
        remaining_axis_titles = []
        for index, title in axis_titles.iterrows():
            if index not in [pair['title'] for pair in best_title_axis_pairs]:
                remaining_axis_titles.append(title['text'])
        print("There seems to be something wrong with the identification of the axis as there are more axis titles than axis. The titles that could not be matched with an axis are:\n", remaining_axis_titles)

    # we can now compare the sizes of the titles and axis lists to see if there are more axis than titles
    elif len(axis_titles) < len(axis_box_data_list):
        # there are more axis than titles, we need to add the remaining axis to the axis titles
        # For the sizes we use the data of the bounding boxes of the axis and set the ids to -1 to indicate that they are not from the original csv file
        for axis in axis_box_data_list:
            if axis['axis_name']+'title' not in axis_titles['type'].values:
                axis_titles = axis_titles.append({'id': -1, 'type': axis['axis_name'] + 'title', 'x': axis['x_min'], 'y': axis['y_min'], 'width': axis['x_max']-axis['x_min'], 'height': axis['y_max']-axis['y_min'], 'text': ' '}, ignore_index=True)
    
    return axis_titles

def min_distance(rect1, rect2):
    """
    Calculate the minimum distance between the surfaces of two rectangles. 
    (Needed for mapping the axis titles to the corresponding axis)

    Args:
    rect1 (tuple): Tuple representing rectangle 1 with the format (x1_left, y1_top, x1_right, y1_bottom)
    rect2 (tuple): Tuple representing rectangle 2 with the format (x2_left, y2_top, x2_right, y2_bottom)

    Returns:
    float: Minimum distance between the surfaces of the two rectangles.
    """

    x1_left, y1_top, x1_right, y1_bottom = rect1
    x2_left, y2_top, x2_right, y2_bottom = rect2

    if x1_left < x2_left:
        dx = x2_left - x1_right
    else:
        dx = x1_left - x2_right

    if y1_top < y2_top:
        dy = y2_top - y1_bottom
    else:
        dy = y1_top - y2_bottom

    if dx > 0 and dy > 0:
        return math.sqrt(dx ** 2 + dy ** 2)
    elif dx > 0:
        return dx
    elif dy > 0:
        return dy
    else:
        return 0

def split_axis_labels(axis_labels, axis, threshold=0.05):
    """
    Function takes in a list of axis labels and which axis it is (can either be 'x' or 'y') and returns a list of dataframes that contain the labels for the individual axis (also updates the 'type' label to represent the different axis)
    """
    different_axis_list = []
    for index, current_label in axis_labels.iterrows():
        bb_start_point = current_label['x'] if axis == 'y' else current_label['y']
        bb_end_point = bb_start_point + current_label['width'] if axis == 'y' else bb_start_point + current_label['height']
        bb_threshold_length = current_label['width'] * threshold if axis == 'y' else current_label['height'] * threshold

        if len(different_axis_list) == 0:       #if the list is empty, we need to add the first element
            different_axis_list.append({'max_bb_range': (bb_start_point, bb_end_point), 'dataframe': pd.DataFrame([current_label])})
        else:                                   #after we iterate over the list to check if the current label fits into one of the existing axis or if we need to create a new one
            for current_axis in different_axis_list:
                current_threshold = (current_axis['max_bb_range'][1] - current_axis['max_bb_range'][0]) * threshold
                if not (bb_end_point + bb_threshold_length < current_axis['max_bb_range'][0] - current_threshold or bb_start_point - bb_threshold_length > current_axis['max_bb_range'][1] + current_threshold):      #if the current label is not out of range from the current axis, we can add it to the current axis
                    current_axis['max_bb_range'] = (min(bb_start_point, current_axis['max_bb_range'][0]), max(bb_end_point, current_axis['max_bb_range'][1]))   # update the range to represent the 'biggest' bounding box
                    current_axis['dataframe'] = current_axis['dataframe'].append(current_label)
                    break
            else:  #if the for loop did not break the current label did not fit into any axis and we need to create a new one
                different_axis_list.append({'max_bb_range': (bb_start_point, bb_end_point), 'dataframe': pd.DataFrame([current_label])})

    # now we sort the axis by their position in the image from left to right (or top to bottom)
    different_axis_list.sort(key=lambda x: x['max_bb_range'][0] + x['max_bb_range'][1]/2)

    # now we need to update the type of the labels to represent the different axis
    for index, current_axis in enumerate(different_axis_list):
        if index == 0:
            current_axis['dataframe']['type'] = axis + '-axis-label'
        else:
            current_axis['dataframe']['type'] = axis + str(index) + '-axis-label'
    result = []
    for current_axis in different_axis_list:
        result.append(current_axis['dataframe'])
    return result
    
def calculate_conistency(range_of_values, threshold=0.05):
    """
    helper function that checks whether all values in the given range have similar values within the threshold. 
    range_of_values: dataframe of values that should be checked. 
    return: True if range is consistent False otherwise
    """
    average_value = range_of_values.mean()
    threshhold_min, threshhold_max = average_value * (1-threshold), average_value * (1+threshold)
    for value in range_of_values:
        if not abs(threshhold_min) < abs(value) < abs(threshhold_max):
            return False
    return True


def detect_misleading_aspect_ratio(d, f):
    """
    Function takes in x,y data and the actual chart to determine whether the aspect ratio is misleading.
    Return: True if the aspect ratio is misleading, otherwise False and an ideal aspect ratio
    """
    df = pd.read_csv(d)
    x = df['x'].to_numpy()
    y = df['y'].to_numpy()

    # make a correction to the slopes

    x_labels, y_labels, x_pos, y_pos = summarize_axes(f, full=True)
    xl_first = extract_float(x_labels[0])
    xl_last = extract_float(x_labels[-1])
    yl_first = extract_float(y_labels[0])
    yl_last = extract_float(y_labels[-1])
    xp_first = float(x_pos[0][0])
    xp_last = float(x_pos[-1][0])
    yp_first = float(y_pos[0][1])
    yp_last = float(y_pos[-1][1])

    # x and y scales PER PIXEL
    x_s = (xl_last - xl_first) / (xp_last - xp_first)
    y_s = (yl_last - yl_first) / (yp_last - yp_first)
    IDEAL_SLOPE = bank_slopes_ms(x, y, scale_x=x_s, scale_y=y_s)
    ACTUAL_SLOPE = calculate_aspect(f)

    # need to check to see if these are off by a factor of sqrt(10)
    greater = 0
    smaller = 0

    if (IDEAL_SLOPE > ACTUAL_SLOPE):
        greater = IDEAL_SLOPE
        smaller = ACTUAL_SLOPE
    else:
        greater = ACTUAL_SLOPE
        smaller = IDEAL_SLOPE

    if greater/smaller < math.sqrt(10):
        # the aspect ratio is not far from the ideal
        return [False]

    if 'log' in comment_axis_scales_util(f):
        print('. Log axis detected. Aspect Ratio is only robust for linear charts at this time.')

    _, _, x_p, _ = summarize_axes(f, full=True)
    last = len(x_p) - 1
    x_p = [float(i) for i in list(x_p[last])]
    return [True, IDEAL_SLOPE]


def comment_axis_scales_util(f):
    """
    Function takes in bounding boxes info and sees if the axes are line or log
    """
    # linear by default
    type_x = 'linear'
    type_y = 'linear'

    x_labels, y_labels, x_pos, y_pos = summarize_axes(f, full=True)
    #need to change the arrays r[0] and r[1] to only contain numbers
    x_labels = [extract_float(i) for i in x_labels]
    y_labels = [extract_float(i) for i in y_labels]
    x_axis_ticks = np.asarray(x_labels).astype(np.float)  # x axis ticks
    y_axis_ticks = np.asarray(y_labels).astype(np.float)  # y axis ticks

    if 0 in x_axis_ticks:
        type_x = 'linear'
    else:
        ## for x_axis ticks, calculate the fit
        x_i = np.arange(0, len(x_axis_ticks), 1)
        lin_fit = np.polyfit(x_i, x_axis_ticks, 1)
        log_fit = np.polyfit(x_i, np.log(x_axis_ticks), 1)

        lin_function = lin_fit[0] * x_i + lin_fit[1]
        log_function = log_fit[0] * x_i + log_fit[1]

        lin_score = r2_score(x_axis_ticks, lin_function)
        log_score = r2_score(np.log(x_axis_ticks), log_function)

        if lin_score > log_score:
            type_x = 'linear'
        else:
            type_x = 'log'

    if 0 in y_axis_ticks:
        type_y = 'linear'
    else:

        y_i = np.arange(0, len(y_axis_ticks), 1)
        lin_fit = np.polyfit(y_i, y_axis_ticks, 1)
        log_fit = np.polyfit(y_i, np.log(y_axis_ticks), 1)

        lin_function = lin_fit[0] * y_i + lin_fit[1]
        log_function = log_fit[0] * y_i + log_fit[1]

        lin_score = r2_score(y_axis_ticks, lin_function)
        log_score = r2_score(np.log(y_axis_ticks), log_function)

        if lin_score > log_score:
            type_y = 'linear'
        else:
            type_y = 'log'

    return type_x, type_y


def find_min_max(d):
    df = pd.read_csv(d)
    x = df['x'].to_numpy()
    y = df['y'].to_numpy()
    min = y.argmin()
    max = y.argmax()
    return x[min], y[min], x[max], y[max]


def parse_num(num):
    try:
        return extract_float(num)
    except:
        pass
    try:
        return int(''.join(c for c in num if c.isdigit()))
    except:
        print("Nan detected")


def identify_origin(filename, use='truncate'):
    """ Takes csv file in poco and heer and returns the coordinates of the
    origin. This is done by taking the bottom y-axis label and the left x-axis
    label
    """
    df = pd.read_csv(filename)
    df = df[['text', 'type', 'x', 'y']]  # drop all others, only need 'text' and 'type'
    y_labels = []
    x_labels = []
    x_pos = []
    y_pos = []
    for text, type, horiz_order, vert_order in zip(df['text'], df['type'], df['x'], df['y']):
        if (type == 'y-axis-label'):
            y_labels.append(text)
            y_pos.append(vert_order)
        elif (type == 'x-axis-label'):
            x_labels.append(text)
            x_pos.append(horiz_order)
        else:
            continue

    y_labels.reverse()  # reverse the y axis labels since the are read top to bottom
    reorder = np.asarray(x_pos).argsort()
    x_labels = np.asarray(x_labels)[reorder]
    x_pos = np.asarray(x_pos)[reorder]
    ######
    x_left = float(x_pos[0])
    y_bottom = float(y_pos[-1])

    if use == 'truncate':
        return (x_left, y_bottom + 50)
    else:
        return (x_left, y_bottom - 50)


def summarize_axes(filename, full=False):
    """
    Takes a csv file in the format of Poco and Heer InfoVis 2017 and returns
    a summary of the axes (axis ranges)
    Full=true returns the contents of all x and y axis labels together with their x and y coordinates
    """
    df = pd.read_csv(filename)
    df = df[['text', 'type', 'x', 'y']]  # drop all others, only need 'text' and 'type'
    y_tick_labels = []
    y_tick_pos = []
    x_tick_labels = []
    x_tick_pos = []
    x_order_tracker = []
    y_order_tracker = []
    for text, type_, x_c, y_c in zip(df['text'], df['type'], df['x'], df['y']):
        if (type_ == 'y-axis-label'):
            y_tick_labels.append(text)
            y_order_tracker.append(y_c)

            y_tick_pos.append([x_c, y_c])
        elif (type_ == 'x-axis-label'):
            x_tick_labels.append(text)
            x_order_tracker.append(x_c)
            x_tick_pos.append([x_c, y_c])
        else:
            continue

    reorder_y = np.asarray(y_order_tracker).argsort()
    y_tick_labels = np.asarray(y_tick_labels)[reorder_y]
    y_tick_pos = np.asarray(y_tick_pos)[reorder_y]
    y_tick_labels = y_tick_labels.tolist()
    y_tick_labels.reverse()

    reorder = np.asarray(x_order_tracker).argsort()
    x_tick_labels = np.asarray(x_tick_labels)[reorder]
    x_tick_labels = x_tick_labels.tolist()
    x_tick_pos = np.asarray(x_tick_pos)[reorder]

    x_range = [x_tick_labels[0], x_tick_labels[-1]]
    y_range = [y_tick_labels[0], y_tick_labels[-1]]

    x_increment = parse_num(x_tick_labels[1]) - parse_num(x_tick_labels[0])
    y_increment = parse_num(y_tick_labels[1]) - parse_num(y_tick_labels[0])

    # print("Summary:\nThe x-axis is bounded by ", x_range,
    #       "\nThe y-axis is bounded by", y_range,
    #       "\nThe x-axis increments by", x_increment,
    #       "\nThe y-axis increments by", y_increment)
    if full == False:
        return x_range, y_range, x_increment, y_increment
    else:
        return x_tick_labels, y_tick_labels, x_tick_pos, y_tick_pos


def calculate_aspect_helper(p1, p2):
    """Calculates the aspect ratio of two non-colinear points
    Takes in a list of two items and returns a value, aspect ratio"""
    assert (len(p1) == 2)
    assert (len(p1) == len(p2))
    y = p2[1] - p1[1]
    x = p2[0] - p1[0]
    return float(x / y)


def calculate_aspect(filename):
    text_roles = pd.read_csv(filename)

    y_axis_labels = dict()
    y_axis_labels['label'] = []
    y_axis_labels['position'] = []
    x_axis_labels = dict()
    x_axis_labels['label'] = []
    x_axis_labels['position'] = []

    x_order_tracker = []

    for i in text_roles.iterrows():
        data = i[1]
        if (data['type'] == 'y-axis-label'):
            y_axis_labels['label'].append(data['text'])
            y_axis_labels['position'].append([data['x'], data['y'], data['width'], data['height']])
        elif (data['type'] == 'x-axis-label'):
            x_axis_labels['label'].append(data['text'])
            x_axis_labels['position'].append([data['x'], data['y'], data['width'], data['height']])
            x_order_tracker.append(data['x'])

    y_axis = []
    for i in y_axis_labels.values():
        y_axis.append(i)
    # y_axis [ 0 for values, 1 for bounding boxes] [ index/length ] [0-3: x,y,width,height]

    reorder = np.asarray(x_order_tracker).argsort()
    x_axis_labels['label'] = np.asarray(x_axis_labels['label'])[reorder]
    x_axis_labels['position'] = np.asarray(x_axis_labels['position'])[reorder]
    x_axis = []
    for i in x_axis_labels.values():
        x_axis.append(i)
    # top left is the top right corner of rhte topmost y-axis label
    top_left = [y_axis[1][0][0] + y_axis[1][0][2], y_axis[1][0][1] + y_axis[1][0][3]]
    # bottom right is the topright corner of the right most
    bottom_right = [x_axis[1][-1][0] + x_axis[1][-1][2], x_axis[1][-1][1] + x_axis[1][-1][3]]

    ar = calculate_aspect_helper(top_left, bottom_right)
    return ar


# bank45
def calc_slopes(x, y, cull=False, scale_x=1, scale_y=1):
    """Calculate slopes of a line given x and y coordinates"""
    dx = abs(np.diff(x)) * scale_x
    dy = np.diff(y) * scale_y
    s = dy / dx
    touse = None
    if cull:
        touse = abs(s) > 0 and np.isfinite(s)
    else:
        touse = np.isfinite(s)
    s = s[touse]
    dx = dx[touse]
    dy = dy[touse]
    Rx = max(x) - min(x)
    Rx *= scale_x
    Ry = max(y) - min(y)
    Ry *= scale_y
    return s, dx, dy, Rx, Ry


def bank_slopes_ms(x, y, cull=False, scale_x=1, scale_y=1):
    """Calculate the median slope of a line given x and y coordinates"""
    s, dx, dy, Rx, Ry = calc_slopes(x, y, scale_x=scale_x, scale_y=scale_y)
    xyrat = ms_helper(s, dx, dy, Rx, Ry)
    return xyrat


def ms_helper(s, dx, dy, Rx, Ry, cull=False):
    """Calculates the median slope of a line"""
    # print(s)
    # print("s for slopes? in line 435")
    # print("note to calculate angles")
    ret = np.median(abs(s)) * Rx / Ry
    return abs(ret)


def fix_non_linear_scales(graph_data, axis_ticks, direction):
    """
    We assume the csv files that save the graph values are created assuming a linear scale.
    When a non-linear scale is detected, this function will transform the values to fit the scale.
    We assume the values at the start of the scale is correctly aligned with the values of the graph.
    graph_data is a list of dictionaries, each dictionary has a key "x" and "y" with the corresponding values
    axis_ticks is a list of dictionaries, each dictionary has a key "value" and "pos" with the corresponding values
    axis_type is either "x" or "y"
    """

    scale_still_linear = True                   # we assume the scale starts linear
    list_of_values = []
    list_of_positions = []
    value_per_tick_factor_previous = 1       # this is the factor that is used to store the value per pixel from the previous tick

    for start, end in zip(axis_ticks[:-1], axis_ticks[1:]):
        interval = {'value_diff': end['value'] - start['value'], 'pos_diff': end['pos'] - start['pos']}
        if scale_still_linear:                              # if the scale is still linear, we can calculate the average value per pixel
            list_of_values.append(interval['value_diff'])
            list_of_positions.append(interval['pos_diff'])
            if not calculate_conistency(pd.DataFrame(list_of_values, columns=['items'])['items']) and not calculate_conistency(pd.DataFrame(list_of_positions, columns=['items'])['items']): # when either the values or the positions are not consistent, we know the scale for this tick is not linear
                scale_still_linear = False
                value_per_tick_factor_previous = (sum(list_of_values)/len(list_of_values)) / (sum(list_of_positions)/len(list_of_positions)) # factor describes how much many value points there are per pixel on average in the linear part of the scale
        if not scale_still_linear:                            # we do not use else here because that would skip the first non-linear tick where we adjust scale_still_linear   
            value_per_tick_factor_local = interval['value_diff'] / interval['pos_diff']
            tick_start_value = start['value']
            local_change_factor = value_per_tick_factor_local/value_per_tick_factor_previous
            for point in graph_data:
                if point[direction] > tick_start_value:      # All points after the tick start value are on a non-linear scale and will be adjusted
                    point[direction] = (point[direction] - tick_start_value) * local_change_factor + tick_start_value
            value_per_tick_factor_previous = value_per_tick_factor_local
    return graph_data

def extract_float(string):
    """
    Extracts a float from a string to be able to handle axis labels that contain characters like '$' or '%'
    Requires the string to contain a number and the comma seperator to be a dot
    If the string is already a float or int, it will return the same value
    If the string does not contain a number, it will return None
    """
    if isinstance(string, str):
        # remove all commas as they are often used as a thousands seperator
        string = string.replace(',', '')
        list_of_extracted_numbers = re.findall(r"[-+]?(?:\d*\.*\d+)", string)
        return float(list_of_extracted_numbers[0])      #return the first if multiple were found
    elif isinstance(string, (int, float)):
        return string
    else:
        return None
    
def extract_axis_data(box_data, axis_name):
    """
    Extracts the title and tick labels of the given axis from the box_data
    returns a dictionary containing the axis title and a list of axis ticks
    """
    direction = 'y' if 'y' in axis_name else 'x'
    df = pd.read_csv(box_data)
    axis_title = df.loc[df['type'] == axis_name + '-title']
    if axis_title.empty:
        axis_title = ' '
    else:
        axis_title = axis_title['text'].values[0]
    axis_labels = df.loc[df['type'] == axis_name + '-label']
    # need to sort the axis labels by their position on the axis so we dont depend on the order in the csv file
    axis_labels.sort_values(by=[direction], ascending= True if direction == 'x' else False, inplace=True)
    ticks = []
    for value, pos in axis_labels[['text', direction]].values:
        o = {}
        o['value'] = extract_float(value)
        o['pos'] = float(pos)
        ticks.append(o)
    return {'title': axis_title, 'ticks': ticks}

def get_chart_title(box_data):
    """
    Extracts the title of the chart
    Returns the title or an empty string if no title was found
    """
    df = pd.read_csv(box_data)
    chart_title = df.loc[df['type'] == 'title']
    if chart_title.empty:
        return ' '
    else:
        return chart_title['text'].values[0]
"""
Common utilities for ASCII image and video processing.
"""
import sys
import argparse
from dataclasses import dataclass
from functools import partial
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageColor

# Characters from darkest to lightest (White text on black background means @ is brightest)
ASCII_CHARS = [" ", ".", ",", "-", "~", "+", "=", "@", "#", "%", "$"]

# ASCII block characters from darkest to lightest
ASCII_BLOCKS = [" ", "░", "▒", "▓", "█"]

# Alphabet letters from darkest to lightest (measured brightness order)
# Space is added at the beginning for the darkest color
ASCII_ALPHABET = [' ', 'r', 'j', 'v', 'x', 'c', 'z', 'l', 'Y', 'L', 'n', 'u', 's', 'y', 'J', 'w', 'i', 't', 'T', 'f', 'C', 'o', 'V', 'I', 'k', 'F', 'S', 'h', 'X', 'a', 'Z', 'm', 'A', 'p', 'q', 'U', 'P', 'e', 'K', 'G', 'b', 'd', 'O', 'H', 'E', 'g', 'D', 'Q', 'R', 'W', 'M', 'B', 'N']

# Digits from darkest to lightest (measured brightness order)
# Space is added at the beginning for the darkest color
ASCII_DIGITS = [' ', '7', '1', '2', '4', '3', '5', '6', '9', '8', '0']

# Alphanumeric characters (letters + digits) from darkest to lightest (measured brightness order)
# Space is added at the beginning for the darkest color
ASCII_ALPHANUMERIC = [' ', 'r', 'v', 'x', 'c', 'z', 'l', '7', 'j', 'Y', 'L', 'n', 'u', 's', 'y', 'J', 'w', 'i', '1', 't', 'T', 'f', 'C', 'o', 'V', 'I', '2', 'k', 'F', 'S', 'h', 'X', '4', 'a', 'Z', '3', 'm', 'A', '5', 'p', 'q', 'U', 'P', 'e', 'K', 'G', 'b', 'd', '6', '9', 'O', 'H', 'E', 'g', 'D', 'Q', 'R', '8', 'W', 'M', 'B', 'N', '0']

# Braille dots from darkest (empty) to lightest (full cell), by dot density
ASCII_DOTS = [' ', '⠁', '⠃', '⠇', '⠏', '⠟', '⠿', '⡿', '⣿']

# Sub-cell shape sets: index is a bit pattern over the cell's subcells,
# bit 0 = top-left, filled row by row (LSB first). Covers every pattern, so a
# cell is encoded exactly instead of approximated by brightness.
QUADRANT_CHARS = [
    ' ', '▘', '▝', '▀', '▖', '▌', '▞', '▛',
    '▗', '▚', '▐', '▜', '▄', '▙', '▟', '█',
]

SEXTANT_CHARS = [
    ' ', '🬀', '🬁', '🬂', '🬃', '🬄', '🬅', '🬆',
    '🬇', '🬈', '🬉', '🬊', '🬋', '🬌', '🬍', '🬎',
    '🬏', '🬐', '🬑', '🬒', '🬓', '▌', '🬔', '🬕',
    '🬖', '🬗', '🬘', '🬙', '🬚', '🬛', '🬜', '🬝',
    '🬞', '🬟', '🬠', '🬡', '🬢', '🬣', '🬤', '🬥',
    '🬦', '🬧', '▐', '🬨', '🬩', '🬪', '🬫', '🬬',
    '🬭', '🬮', '🬯', '🬰', '🬱', '🬲', '🬳', '🬴',
    '🬵', '🬶', '🬷', '🬸', '🬹', '🬺', '🬻', '█',
]

OCTANT_CHARS = [
    ' ', '\U0001cea8', '\U0001ceab', '🮂', '\U0001cd00', '▘', '\U0001cd01', '\U0001cd02',
    '\U0001cd03', '\U0001cd04', '▝', '\U0001cd05', '\U0001cd06', '\U0001cd07', '\U0001cd08', '▀',
    '\U0001cd09', '\U0001cd0a', '\U0001cd0b', '\U0001cd0c', '\U0001fbe6', '\U0001cd0d', '\U0001cd0e', '\U0001cd0f',
    '\U0001cd10', '\U0001cd11', '\U0001cd12', '\U0001cd13', '\U0001cd14', '\U0001cd15', '\U0001cd16', '\U0001cd17',
    '\U0001cd18', '\U0001cd19', '\U0001cd1a', '\U0001cd1b', '\U0001cd1c', '\U0001cd1d', '\U0001cd1e', '\U0001cd1f',
    '\U0001fbe7', '\U0001cd20', '\U0001cd21', '\U0001cd22', '\U0001cd23', '\U0001cd24', '\U0001cd25', '\U0001cd26',
    '\U0001cd27', '\U0001cd28', '\U0001cd29', '\U0001cd2a', '\U0001cd2b', '\U0001cd2c', '\U0001cd2d', '\U0001cd2e',
    '\U0001cd2f', '\U0001cd30', '\U0001cd31', '\U0001cd32', '\U0001cd33', '\U0001cd34', '\U0001cd35', '🮅',
    '\U0001cea3', '\U0001cd36', '\U0001cd37', '\U0001cd38', '\U0001cd39', '\U0001cd3a', '\U0001cd3b', '\U0001cd3c',
    '\U0001cd3d', '\U0001cd3e', '\U0001cd3f', '\U0001cd40', '\U0001cd41', '\U0001cd42', '\U0001cd43', '\U0001cd44',
    '▖', '\U0001cd45', '\U0001cd46', '\U0001cd47', '\U0001cd48', '▌', '\U0001cd49', '\U0001cd4a',
    '\U0001cd4b', '\U0001cd4c', '▞', '\U0001cd4d', '\U0001cd4e', '\U0001cd4f', '\U0001cd50', '▛',
    '\U0001cd51', '\U0001cd52', '\U0001cd53', '\U0001cd54', '\U0001cd55', '\U0001cd56', '\U0001cd57', '\U0001cd58',
    '\U0001cd59', '\U0001cd5a', '\U0001cd5b', '\U0001cd5c', '\U0001cd5d', '\U0001cd5e', '\U0001cd5f', '\U0001cd60',
    '\U0001cd61', '\U0001cd62', '\U0001cd63', '\U0001cd64', '\U0001cd65', '\U0001cd66', '\U0001cd67', '\U0001cd68',
    '\U0001cd69', '\U0001cd6a', '\U0001cd6b', '\U0001cd6c', '\U0001cd6d', '\U0001cd6e', '\U0001cd6f', '\U0001cd70',
    '\U0001cea0', '\U0001cd71', '\U0001cd72', '\U0001cd73', '\U0001cd74', '\U0001cd75', '\U0001cd76', '\U0001cd77',
    '\U0001cd78', '\U0001cd79', '\U0001cd7a', '\U0001cd7b', '\U0001cd7c', '\U0001cd7d', '\U0001cd7e', '\U0001cd7f',
    '\U0001cd80', '\U0001cd81', '\U0001cd82', '\U0001cd83', '\U0001cd84', '\U0001cd85', '\U0001cd86', '\U0001cd87',
    '\U0001cd88', '\U0001cd89', '\U0001cd8a', '\U0001cd8b', '\U0001cd8c', '\U0001cd8d', '\U0001cd8e', '\U0001cd8f',
    '▗', '\U0001cd90', '\U0001cd91', '\U0001cd92', '\U0001cd93', '▚', '\U0001cd94', '\U0001cd95',
    '\U0001cd96', '\U0001cd97', '▐', '\U0001cd98', '\U0001cd99', '\U0001cd9a', '\U0001cd9b', '▜',
    '\U0001cd9c', '\U0001cd9d', '\U0001cd9e', '\U0001cd9f', '\U0001cda0', '\U0001cda1', '\U0001cda2', '\U0001cda3',
    '\U0001cda4', '\U0001cda5', '\U0001cda6', '\U0001cda7', '\U0001cda8', '\U0001cda9', '\U0001cdaa', '\U0001cdab',
    '▂', '\U0001cdac', '\U0001cdad', '\U0001cdae', '\U0001cdaf', '\U0001cdb0', '\U0001cdb1', '\U0001cdb2',
    '\U0001cdb3', '\U0001cdb4', '\U0001cdb5', '\U0001cdb6', '\U0001cdb7', '\U0001cdb8', '\U0001cdb9', '\U0001cdba',
    '\U0001cdbb', '\U0001cdbc', '\U0001cdbd', '\U0001cdbe', '\U0001cdbf', '\U0001cdc0', '\U0001cdc1', '\U0001cdc2',
    '\U0001cdc3', '\U0001cdc4', '\U0001cdc5', '\U0001cdc6', '\U0001cdc7', '\U0001cdc8', '\U0001cdc9', '\U0001cdca',
    '\U0001cdcb', '\U0001cdcc', '\U0001cdcd', '\U0001cdce', '\U0001cdcf', '\U0001cdd0', '\U0001cdd1', '\U0001cdd2',
    '\U0001cdd3', '\U0001cdd4', '\U0001cdd5', '\U0001cdd6', '\U0001cdd7', '\U0001cdd8', '\U0001cdd9', '\U0001cdda',
    '▄', '\U0001cddb', '\U0001cddc', '\U0001cddd', '\U0001cdde', '▙', '\U0001cddf', '\U0001cde0',
    '\U0001cde1', '\U0001cde2', '▟', '\U0001cde3', '▆', '\U0001cde4', '\U0001cde5', '█',
]

# mode -> (subcells across, subcells down, characters)
SHAPE_MODES = {
    "quadrants": (2, 2, QUADRANT_CHARS),
    "sextants": (2, 3, SEXTANT_CHARS),
    "octants": (2, 4, OCTANT_CHARS),
}

# Cells flatter than this are drawn solid instead of thresholded, to keep
# smooth areas from turning into noise.
SHAPE_CONTRAST_FLOOR = 0.12

# Diagonal wedge glyphs (U+1FB3C-U+1FB67): each fills one corner of the cell,
# cut by a straight line between two edge points. The sub-cell grids above
# quantise every edge to their own rectangles; a wedge places its edge at an
# arbitrary angle, so slanted contours stay smooth instead of stair-stepping.
# Cell coordinates run 0..1, y downwards. Unicode names the thirds on the side
# edges and the centre on the top and bottom edges.
WEDGE_POINTS = {
    "ul": (0.0, 0.0), "uc": (0.5, 0.0), "ur": (1.0, 0.0),
    "ll": (0.0, 1.0), "lc": (0.5, 1.0), "lr": (1.0, 1.0),
    "uml": (0.0, 1 / 3), "lml": (0.0, 2 / 3), "ml": (0.0, 0.5),
    "umr": (1.0, 1 / 3), "lmr": (1.0, 2 / 3), "mr": (1.0, 0.5),
    "cc": (0.5, 0.5),
}

# char, corner kept, cut endpoints.
WEDGE_CUTS = [
    ("🬼", "ll", "lml", "lc"),  # U+1FB3C
    ("🬽", "ll", "lml", "lr"),  # U+1FB3D
    ("🬾", "ll", "uml", "lc"),  # U+1FB3E
    ("🬿", "ll", "uml", "lr"),  # U+1FB3F
    ("🭀", "ll", "ul", "lc"),  # U+1FB40
    ("🭁", "lr", "uml", "uc"),  # U+1FB41
    ("🭂", "lr", "uml", "ur"),  # U+1FB42
    ("🭃", "lr", "lml", "uc"),  # U+1FB43
    ("🭄", "lr", "lml", "ur"),  # U+1FB44
    ("🭅", "lr", "ll", "uc"),  # U+1FB45
    ("🭆", "lr", "lml", "umr"),  # U+1FB46
    ("🭇", "lr", "lc", "lmr"),  # U+1FB47
    ("🭈", "lr", "ll", "lmr"),  # U+1FB48
    ("🭉", "lr", "lc", "umr"),  # U+1FB49
    ("🭊", "lr", "ll", "umr"),  # U+1FB4A
    ("🭋", "lr", "lc", "ur"),  # U+1FB4B
    ("🭌", "ll", "uc", "umr"),  # U+1FB4C
    ("🭍", "ll", "ul", "umr"),  # U+1FB4D
    ("🭎", "ll", "uc", "lmr"),  # U+1FB4E
    ("🭏", "ll", "ul", "lmr"),  # U+1FB4F
    ("🭐", "ll", "uc", "lr"),  # U+1FB50
    ("🭑", "ll", "uml", "lmr"),  # U+1FB51
    ("🭒", "ur", "lml", "lc"),  # U+1FB52
    ("🭓", "ur", "lml", "lr"),  # U+1FB53
    ("🭔", "ur", "uml", "lc"),  # U+1FB54
    ("🭕", "ur", "uml", "lr"),  # U+1FB55
    ("🭖", "ur", "ul", "lc"),  # U+1FB56
    ("🭗", "ul", "uml", "uc"),  # U+1FB57
    ("🭘", "ul", "uml", "ur"),  # U+1FB58
    ("🭙", "ul", "lml", "uc"),  # U+1FB59
    ("🭚", "ul", "lml", "ur"),  # U+1FB5A
    ("🭛", "ul", "ll", "uc"),  # U+1FB5B
    ("🭜", "ul", "lml", "umr"),  # U+1FB5C
    ("🭝", "ul", "lc", "lmr"),  # U+1FB5D
    ("🭞", "ul", "ll", "lmr"),  # U+1FB5E
    ("🭟", "ul", "lc", "umr"),  # U+1FB5F
    ("🭠", "ul", "ll", "umr"),  # U+1FB60
    ("🭡", "ul", "lc", "ur"),  # U+1FB61
    ("🭢", "ur", "uc", "umr"),  # U+1FB62
    ("🭣", "ur", "ul", "umr"),  # U+1FB63
    ("🭤", "ur", "uc", "lmr"),  # U+1FB64
    ("🭥", "ur", "ul", "lmr"),  # U+1FB65
    ("🭦", "ur", "uc", "lr"),  # U+1FB66
    ("🭧", "ur", "uml", "lmr"),  # U+1FB67
    # The half blocks are the same construction with an axis-aligned cut.
    ("▀", "ul", "ml", "mr"),
    ("▄", "ll", "ml", "mr"),
    ("▌", "ul", "uc", "lc"),
    ("▐", "ur", "uc", "lc"),
]

# Triangles meeting at the cell centre: quarter block, its three-quarter
# complement, and the quarter's corners (U+1FB6C-U+1FB6F / U+1FB68-U+1FB6B).
WEDGE_TRIANGLES = [
    ("🭬", "🭨", ("ul", "cc", "ll")),
    ("🭭", "🭩", ("ul", "ur", "cc")),
    ("🭮", "🭪", ("ur", "lr", "cc")),
    ("🭯", "🭫", ("ll", "cc", "lr")),
]

# Samples per cell side when fitting a glyph to a cell. Coverage is fractional,
# so a cut need not land on a sample boundary to be represented.
MASK_RES = 8

def _side(a, b, x, y):
    """Signed side of the line a-b, positive on one half plane."""
    return (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])

def _cut_cover(corner, start, end, x, y):
    """1 on the corner's side of the cut, 0 beyond it, 1/2 exactly on it."""
    a, b = WEDGE_POINTS[start], WEDGE_POINTS[end]
    kept = _side(a, b, x, y) * _side(a, b, *WEDGE_POINTS[corner])
    return np.where(kept > 0, 1.0, np.where(kept < 0, 0.0, 0.5))

def _triangle_cover(points, x, y):
    p = [WEDGE_POINTS[key] for key in points]
    sides = np.stack([_side(p[i], p[(i + 1) % 3], x, y) for i in range(3)])
    inside = (sides >= 0).all(axis=0) | (sides <= 0).all(axis=0)
    return np.where(inside & (sides == 0).any(axis=0), 0.5, inside.astype(np.float32))

def _subcell_cover(pattern, sub_x, sub_y, x, y):
    col = np.minimum((x * sub_x).astype(int), sub_x - 1)
    row = np.minimum((y * sub_y).astype(int), sub_y - 1)
    return ((pattern >> (row * sub_x + col)) & 1).astype(np.float32)

def glyph_coverage(cover, width, height, supersample=6):
    """Fractional coverage of a glyph over a (height, width) sample grid."""
    xs = (np.arange(width * supersample) + 0.5) / (width * supersample)
    ys = (np.arange(height * supersample) + 0.5) / (height * supersample)
    x, y = np.meshgrid(xs, ys)
    covered = np.broadcast_to(cover(x, y), x.shape).astype(np.float32)
    return covered.reshape(height, supersample, width, supersample).mean(axis=(1, 3))

def _wedge_glyphs():
    glyphs = [(" ", lambda x, y: np.zeros(x.shape, np.float32)),
              ("█", lambda x, y: np.ones(x.shape, np.float32))]
    glyphs += [(char, partial(_cut_cover, corner, start, end))
               for char, corner, start, end in WEDGE_CUTS]
    for quarter, rest, points in WEDGE_TRIANGLES:
        cover = partial(_triangle_cover, points)
        glyphs.append((quarter, cover))
        glyphs.append((rest, lambda x, y, cover=cover: 1.0 - cover(x, y)))
    return glyphs

def _subcell_glyphs(mode):
    sub_x, sub_y, chars = SHAPE_MODES[mode]
    return [(char, partial(_subcell_cover, pattern, sub_x, sub_y))
            for pattern, char in enumerate(chars)]

def _unique_glyphs(glyphs):
    seen = {}
    for char, cover in glyphs:
        seen.setdefault(char, cover)
    return list(seen.items())

MASK_GLYPHS = {
    "wedges": _wedge_glyphs(),
    "wedges-octants": _unique_glyphs(_wedge_glyphs() + _subcell_glyphs("octants")),
}

def _mask_palette(glyphs):
    """Glyph characters and their coverage vectors, flattened for matching."""
    chars = [char for char, _ in glyphs]
    masks = np.stack([glyph_coverage(cover, MASK_RES, MASK_RES).ravel() for _, cover in glyphs])
    return chars, masks

MASK_MODES = {mode: _mask_palette(glyphs) for mode, glyphs in MASK_GLYPHS.items()}

def _complement_pairs(masks):
    """
    One representative per complementary glyph pair, with its mate. Both alphabets
    are closed under complement, and a pair splits a cell identically, so scoring
    one of each is enough - which half is drawn is decided by brightness.
    """
    index = {np.round(mask, 4).tobytes(): i for i, mask in enumerate(masks)}
    mates = np.array([index[np.round((1.0 - mask).astype(np.float32), 4).tobytes()] for mask in masks])
    reps = np.flatnonzero(np.arange(len(masks)) < mates)
    return reps, mates[reps]

MASK_PAIRS = {mode: _complement_pairs(masks) for mode, (_, masks) in MASK_MODES.items()}

ANSI_RESET = "\x1b[0m"

@dataclass
class AsciiFrameOptions:
    """Options for processing a frame into ASCII art."""
    char_palette: np.ndarray  # Pre-rendered character palette, shape (num_chars, char_h, char_w, 3)
    char_w: int  # Character width in pixels
    char_h: int  # Character height in pixels
    invert_brightness: bool = False  # If True, invert brightness mapping
    num_chars: int = None  # Number of characters in palette (if None, uses len(char_palette))
    preserve_colors: bool = False  # If True, preserve original colors and skip grayscale/normalization
    bg_color: tuple = (0, 0, 0)  # Background color tuple (RGB) - used for color preservation
    fg_color: tuple = (255, 255, 255)  # Foreground color tuple (RGB) - used for color preservation
    swap_dims: bool = False  # If True, swap h and w (for rotated videos)
    mode: str = "chars"  # Character set name (shape modes select glyphs by sub-cell pattern)
    tint_color: tuple = None  # Tint color tuple (RGB) - applied when preserve_colors is True

MODE_CHARS = {
    "chars": ASCII_CHARS,
    "blocks": ASCII_BLOCKS,
    "alphabet": ASCII_ALPHABET,
    "digits": ASCII_DIGITS,
    "alphanumeric": ASCII_ALPHANUMERIC,
    "dots": ASCII_DOTS,
    "quadrants": QUADRANT_CHARS,
    "sextants": SEXTANT_CHARS,
    "octants": OCTANT_CHARS,
    "wedges": MASK_MODES["wedges"][0],
    "wedges-octants": MASK_MODES["wedges-octants"][0],
}

def select_chars(mode="chars"):
    """Return the character set list based on mode."""
    return MODE_CHARS[mode]

def is_shape_mode(mode):
    """True for modes that encode sub-cell shape instead of brightness."""
    return mode in SHAPE_MODES or mode in MASK_MODES

def is_mask_mode(mode):
    """True for shape modes whose glyphs are fitted by coverage, not by bit pattern."""
    return mode in MASK_MODES

def split_cells(img, rows, cols, sub_x, sub_y):
    """Resize to sub-cell resolution and group as (rows, cols, subcells[, channels])."""
    sub = cv2.resize(img, (cols * sub_x, rows * sub_y), interpolation=cv2.INTER_AREA).astype(np.float32)
    if sub.ndim == 2:
        return sub.reshape(rows, sub_y, cols, sub_x).transpose(0, 2, 1, 3).reshape(rows, cols, sub_y * sub_x)
    channels = sub.shape[2]
    return (sub.reshape(rows, sub_y, cols, sub_x, channels).transpose(0, 2, 1, 3, 4)
               .reshape(rows, cols, sub_y * sub_x, channels))

def shape_lit_mask(img_gray, rows, cols, mode, invert_brightness=False):
    """
    Decide which subcells are lit, thresholding every cell at its own midpoint
    so edges stay sharp. Returns a bool array (rows, cols, subcells).
    """
    gray_min, gray_max = img_gray.min(), img_gray.max()
    cells = split_cells(img_gray, rows, cols, *SHAPE_MODES[mode][:2])
    cells = (cells - gray_min) / (gray_max - gray_min) if gray_max > gray_min else cells / 255.0

    cell_min = cells.min(axis=-1, keepdims=True)
    cell_max = cells.max(axis=-1, keepdims=True)

    lit = cells > (cell_min + cell_max) / 2
    flat = (cell_max - cell_min) < SHAPE_CONTRAST_FLOOR
    lit = np.where(flat, cells.mean(axis=-1, keepdims=True) > 0.5, lit)
    return ~lit if invert_brightness else lit

def shape_indices_from_lit(lit):
    """Pack a lit mask into a sub-cell bit pattern (index into the mode's char list)."""
    weights = (1 << np.arange(lit.shape[-1])).astype(np.int64)
    return (lit * weights).sum(axis=-1)

def shape_indices(img_gray, rows, cols, mode, invert_brightness=False):
    """Map each cell to a sub-cell bit pattern (index into the mode's char list)."""
    return shape_indices_from_lit(shape_lit_mask(img_gray, rows, cols, mode, invert_brightness))

def shape_cell_colors(frame, rows, cols, mode, lit):
    """
    Average the source color over lit and unlit subcells separately, so a cell
    can carry two colors. Returns (fg, bg), each (rows, cols, 3).
    """
    cells = split_cells(frame, rows, cols, *SHAPE_MODES[mode][:2])
    lit_f = lit[..., np.newaxis].astype(np.float32)
    lit_count = lit_f.sum(axis=2)
    unlit_count = (1.0 - lit_f).sum(axis=2)
    cell_mean = cells.mean(axis=2)

    fg = np.where(lit_count > 0, (cells * lit_f).sum(axis=2) / np.maximum(lit_count, 1), cell_mean)
    bg = np.where(unlit_count > 0, (cells * (1.0 - lit_f)).sum(axis=2) / np.maximum(unlit_count, 1), cell_mean)
    return fg, bg

def mask_cell_samples(img_gray, rows, cols):
    """Cell samples at MASK_RES x MASK_RES, scaled to 0..1 over the image's range."""
    cells = split_cells(img_gray, rows, cols, MASK_RES, MASK_RES)
    gray_min, gray_max = img_gray.min(), img_gray.max()
    return (cells - gray_min) / (gray_max - gray_min) if gray_max > gray_min else cells / 255.0

def mask_indices(img_gray, rows, cols, mode, invert_brightness=False):
    """
    Fit every glyph to every cell as a two-tone split and keep the best one, so
    wedges and rectangular sub-cells compete on the same per-pixel error. The
    error of a glyph is what its two region means leave behind; dropping the
    constant sum of squares turns that into a quantity to maximize.
    """
    chars, masks = MASK_MODES[mode]
    reps, mates = MASK_PAIRS[mode]
    cells = mask_cell_samples(img_gray, rows, cols)
    samples = cells.reshape(-1, masks.shape[1])

    covered_area = masks[reps].sum(axis=-1)
    bare_area = masks.shape[1] - covered_area
    covered_sum = samples @ masks[reps].T
    total = samples.sum(axis=-1, keepdims=True)
    bare_sum = total - covered_sum

    fit = (np.divide(covered_sum ** 2, covered_area, out=np.zeros_like(covered_sum), where=covered_area > 0)
           + np.divide(bare_sum ** 2, bare_area, out=np.zeros_like(bare_sum), where=bare_area > 0))
    best = fit.argmax(axis=-1)

    # The brighter region is the one the glyph draws, unless brightness is inverted.
    picked = np.take_along_axis(covered_sum, best[:, np.newaxis], axis=1)[:, 0]
    with np.errstate(invalid="ignore", divide="ignore"):
        covered_brighter = picked / covered_area[best] >= (total[:, 0] - picked) / bare_area[best]
    indices = np.where(covered_brighter ^ invert_brightness, reps[best], mates[best])

    # Cells with nothing to split stay solid, so smooth areas do not turn into noise.
    flat = (cells.max(axis=-1) - cells.min(axis=-1)).ravel() < SHAPE_CONTRAST_FLOOR
    flat |= (covered_area[best] == 0) | (bare_area[best] == 0)
    solid = (samples.mean(axis=-1) > 0.5) ^ invert_brightness
    indices = np.where(flat, np.where(solid, chars.index("█"), chars.index(" ")), indices)
    return indices.reshape(rows, cols)

def mask_cell_colors(frame, rows, cols, mode, indices):
    """Average the source color under and outside each chosen glyph. Returns (fg, bg)."""
    _, masks = MASK_MODES[mode]
    cells = split_cells(frame, rows, cols, MASK_RES, MASK_RES)
    covered = masks[indices][..., np.newaxis]
    lit_count = covered.sum(axis=2)
    unlit_count = (1.0 - covered).sum(axis=2)
    cell_mean = cells.mean(axis=2)

    fg = np.where(lit_count > 1e-6, (cells * covered).sum(axis=2) / np.maximum(lit_count, 1e-6), cell_mean)
    bg = np.where(unlit_count > 1e-6, (cells * (1.0 - covered)).sum(axis=2) / np.maximum(unlit_count, 1e-6), cell_mean)
    return fg, bg

def apply_tint(colors, tint_color):
    """Multiply colors by a tint, as the raster path does."""
    if tint_color is None:
        return colors
    return colors * (np.array(tint_color, dtype=np.float32) / 255.0)

def sgr(fg=None, bg=None):
    """24-bit color escape for a foreground and/or background."""
    codes = []
    if fg is not None:
        codes.append("38;2;%d;%d;%d" % tuple(fg))
    if bg is not None:
        codes.append("48;2;%d;%d;%d" % tuple(bg))
    return "\x1b[%sm" % ";".join(codes) if codes else ""

def ansi_text(indices, chars, fg, bg=None):
    """
    Join cells into colored lines. A color is emitted only when it changes and
    only when the glyph shows it - a blank cell needs no foreground, a full
    block no background.
    """
    fg = np.clip(fg, 0, 255).round().astype(int)
    bg = None if bg is None else np.clip(bg, 0, 255).round().astype(int)

    lines = []
    for row in range(indices.shape[0]):
        parts = []
        current_fg = current_bg = None
        for col in range(indices.shape[1]):
            char = chars[indices[row, col]]
            cell_fg = tuple(fg[row, col]) if char != " " else None
            cell_bg = tuple(bg[row, col]) if bg is not None and char != "█" else None

            if cell_fg == current_fg:
                cell_fg = None
            elif cell_fg is not None:
                current_fg = cell_fg
            if cell_bg == current_bg:
                cell_bg = None
            elif cell_bg is not None:
                current_bg = cell_bg

            parts.append(sgr(cell_fg, cell_bg))
            parts.append(char)
        parts.append(ANSI_RESET)
        lines.append("".join(parts))
    return "\n".join(lines)

def render_shape_palette(char_width, char_height, bg_color, fg_color, mode):
    """
    Draw the sub-cell glyphs as rectangles instead of using the font.
    No font covers the sextant/octant ranges, and drawn cells tile seamlessly.
    Returns a numpy array of shape (num_chars, h, w, 3).
    """
    sub_x, sub_y, chars = SHAPE_MODES[mode]
    xs = np.linspace(0, char_width, sub_x + 1).round().astype(int)
    ys = np.linspace(0, char_height, sub_y + 1).round().astype(int)

    palette = np.empty((len(chars), char_height, char_width, 3), dtype=np.uint8)
    palette[:] = np.array(bg_color, dtype=np.uint8)
    for pattern in range(len(chars)):
        for bit in range(sub_x * sub_y):
            if pattern >> bit & 1:
                row, col = divmod(bit, sub_x)
                palette[pattern, ys[row]:ys[row + 1], xs[col]:xs[col + 1]] = fg_color
    return palette

def render_mask_palette(char_width, char_height, bg_color, fg_color, mode):
    """
    Draw the fitted glyphs by coverage, blending fg over bg so a slanted cut is
    antialiased instead of stepped. Returns a numpy array (num_chars, h, w, 3).
    """
    coverage = np.stack([glyph_coverage(cover, char_width, char_height)
                         for _, cover in MASK_GLYPHS[mode]])[..., np.newaxis]
    blended = (np.array(fg_color, dtype=np.float32) * coverage +
               np.array(bg_color, dtype=np.float32) * (1.0 - coverage))
    return blended.round().astype(np.uint8)

def pre_render_chars(font, char_width, char_height, bg_color, fg_color, mode="chars"):
    """
    Renders every ASCII char into a numpy array (stamp) once.
    Returns a numpy array of shape (num_chars, h, w, 3).
    """
    if is_mask_mode(mode):
        return render_mask_palette(char_width, char_height, bg_color, fg_color, mode)
    if is_shape_mode(mode):
        return render_shape_palette(char_width, char_height, bg_color, fg_color, mode)

    chars = select_chars(mode)
    
    # Measure font metrics to establish baseline alignment
    # Use a reference character to set baseline, then ensure all characters fit
    dummy_img = Image.new("RGB", (char_width * 2, char_height * 2))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    # Find the minimum left and top across all characters to establish baseline
    # Use the same measurement approach as measure_font_metrics for consistency
    min_left = float('inf')
    min_top = float('inf')
    for char in chars:
        bbox = dummy_draw.textbbox((0, 0), char, font=font)
        min_left = min(min_left, bbox[0])
        min_top = min(min_top, bbox[1])
    
    # Baseline offset positions characters so the leftmost/topmost aligns at (0,0)
    # Use same calculation as in measure_font_metrics, then round to integer for rendering
    baseline_offset_x = int(round(-min_left))
    baseline_offset_y = int(round(-min_top))
    
    char_images = []
    
    for char in chars:
        # Create a blank image for the character with background color
        img = Image.new("RGB", (char_width, char_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw character at baseline offset position with integer coordinates
        # PIL's text rendering handles antialiasing automatically, which is fine for most cases
        # Using integer positions helps avoid sub-pixel positioning issues
        draw.text((baseline_offset_x, baseline_offset_y), char, font=font, fill=fg_color)
        
        # Convert to numpy array and append
        char_images.append(np.array(img))
    
    return np.stack(char_images)

def load_font(fontsize=10, font_path="/System/Library/Fonts/Menlo.ttc"):
    """
    Load font from path, fallback to default if not found.
    Returns ImageFont object.
    """
    try:
        font = ImageFont.truetype(font_path, fontsize)
        print(f"Font loaded: {font_path}")
        return font
    except IOError:
        font = ImageFont.load_default()
        print("Using default font")
        return font

def parse_colors(bg_color_str, fg_color_str):
    """
    Parse color strings to RGB tuples.
    Returns (bg_color, fg_color) tuple.
    Raises ValueError on invalid color format.
    """
    try:
        bg_color = ImageColor.getcolor(bg_color_str, "RGB")
        fg_color = ImageColor.getcolor(fg_color_str, "RGB")
        return bg_color, fg_color
    except ValueError as e:
        print(f"Error: Invalid color format. {e}")
        sys.exit(1)

def add_common_arguments(parser, input_help="Path to input file", output_help="Path to output file"):
    """
    Add common ASCII processing arguments to an ArgumentParser.
    
    Args:
        parser: argparse.ArgumentParser instance
        input_help: Help text for input argument
        output_help: Help text for output argument
    """
    parser.add_argument("input", help=input_help)
    parser.add_argument("-o", "--output", help=output_help, default=None)
    parser.add_argument("-f", "--fontsize", type=int, help="Font size", default=10)
    parser.add_argument("-s", "--scale", type=float, help="Scale (0.5 is faster)", default=1.0)
    parser.add_argument("--bg-color", help="Background color (e.g., 'black', '#000000')", default="black")
    parser.add_argument("--fg-color", help="Foreground color (e.g., 'white', '#FFFFFF')", default="white")
    parser.add_argument("--invert-brightness", action="store_true", help="Invert brightness mapping (bright areas become dark characters)")
    parser.add_argument("--mode", choices=list(MODE_CHARS.keys()), default="chars", help="Character set: 'chars' (default), 'blocks' (█ ▓ ▒ ░ space), 'alphabet' (a-z, A-Z), 'digits' (0-9), 'alphanumeric' (a-z, A-Z, 0-9), 'dots' (braille ⠁⠿⣿), or the sub-cell shape sets 'quadrants' (2x2 ▘▚▛), 'sextants' (2x3 🬀🬂🬎) and 'octants' (2x4 𜴀𜶮𜷝, sharpest), 'wedges' (diagonal 🬼🭀🭢, smoothest slants) or 'wedges-octants' (per cell, whichever fits better)")
    parser.add_argument("--preserve-colors", action="store_true", help="Preserve original colors (ignores fg-color, disables grayscale and normalization)")
    parser.add_argument("--tint", help="Tint color to apply when --preserve-colors is set (e.g., 'red', '#FF0000')", default=None)
    parser.add_argument("--adjust-aspect-ratio", action="store_true", help="For .txt output, adjust source image AR to compensate for terminal cell aspect (~1:2) so output is not stretched")
    parser.add_argument("--ansi-colors", action="store_true", help="For .txt output, emit 24-bit ANSI color codes taken from the source (shape modes color lit and unlit subcells separately)")
    parser.add_argument("--ansi-fg-only", action="store_true", help="Like --ansi-colors but foreground only, for importers that ignore background codes (e.g. dartboard --read-raw)")

def measure_font_metrics(font):
    """
    Measure character width and height for a given font.
    Measures all characters from all character sets to find maximum dimensions.
    Measures characters as they will be rendered (with baseline alignment).
    Returns (char_width, char_height) tuple.
    """
    # Use a larger temporary image to measure characters
    temp_size = 1000
    dummy_img = Image.new("RGB", (temp_size, temp_size))
    dummy_draw = ImageDraw.Draw(dummy_img)
    
    # Collect all characters from all sets
    all_chars = set(ASCII_CHARS + ASCII_BLOCKS + ASCII_ALPHABET + ASCII_DIGITS + ASCII_ALPHANUMERIC + ASCII_DOTS)
    
    # First pass: find baseline offsets (minimum left and top)
    min_left = float('inf')
    min_top = float('inf')
    for char in all_chars:
        bbox = dummy_draw.textbbox((0, 0), char, font=font)
        min_left = min(min_left, bbox[0])
        min_top = min(min_top, bbox[1])
    
    baseline_offset_x = -min_left
    baseline_offset_y = -min_top
    
    # Second pass: measure each character when drawn at baseline offset position
    # This gives us the actual extents as they will be rendered
    max_right = 0
    max_bottom = 0
    min_rendered_left = float('inf')
    min_rendered_top = float('inf')
    
    for char in all_chars:
        # Measure character when drawn at baseline offset (as it will be rendered)
        bbox = dummy_draw.textbbox((baseline_offset_x, baseline_offset_y), char, font=font)
        min_rendered_left = min(min_rendered_left, bbox[0])
        min_rendered_top = min(min_rendered_top, bbox[1])
        max_right = max(max_right, bbox[2])
        max_bottom = max(max_bottom, bbox[3])
    
    # Calculate dimensions needed to fit all characters in their rendered positions
    char_w = max_right - min_rendered_left
    char_h = max_bottom - min_rendered_top
    
    # Add adaptive padding to prevent clipping
    # Use more generous padding to ensure no clipping occurs
    # For small fonts, use fixed pixel padding; for larger fonts, use percentage
    if char_w < 10:
        padding_w = max(2, int(round(char_w * 0.15)))  # At least 2px or 15% for very small fonts
    elif char_w < 20:
        padding_w = max(2, int(round(char_w * 0.18)))  # At least 2px or 18% for small fonts
    else:
        padding_w = max(4, int(round(char_w * 0.25)))  # At least 4px or 25% for larger fonts
    
    if char_h < 10:
        padding_h = max(2, int(round(char_h * 0.15)))  # At least 2px or 15% for very small fonts
    elif char_h < 20:
        padding_h = max(2, int(round(char_h * 0.18)))  # At least 2px or 18% for small fonts
    else:
        padding_h = max(4, int(round(char_h * 0.25)))  # At least 4px or 25% for larger fonts
    
    # Return integer dimensions
    return int(round(char_w + padding_w)), int(round(char_h + padding_h))

def frame_to_text(frame, char_w, char_h, chars, invert_brightness=False, swap_dims=False, mode="chars",
                  ansi_colors=False, ansi_fg_only=False, tint_color=None):
    """
    Convert a frame (RGB numpy array) into a multi-line ASCII string.
    Uses grayscale + min/max normalization for character selection.
    With ansi_colors, each cell carries 24-bit color escapes taken from the source;
    ansi_fg_only drops the background half, for consumers that ignore it.
    """
    h, w = frame.shape[:2]
    if swap_dims:
        h, w = w, h
    cols = w // char_w
    rows = h // char_h

    img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)

    if is_shape_mode(mode):
        if is_mask_mode(mode):
            indices = mask_indices(img_gray, rows, cols, mode, invert_brightness)
            cell_colors = lambda: mask_cell_colors(frame, rows, cols, mode, indices)
        else:
            lit = shape_lit_mask(img_gray, rows, cols, mode, invert_brightness)
            indices = shape_indices_from_lit(lit)
            cell_colors = lambda: shape_cell_colors(frame, rows, cols, mode, lit)
        if not ansi_colors:
            return "\n".join("".join(chars[idx] for idx in row) for row in indices)
        fg, bg = cell_colors()
        if ansi_fg_only:
            return ansi_text(indices, chars, apply_tint(fg, tint_color))
        return ansi_text(indices, chars, apply_tint(fg, tint_color), apply_tint(bg, tint_color))

    img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

    num_chars = len(chars)
    img_min, img_max = img_small.min(), img_small.max()
    if img_max > img_min:
        img_normalized = (img_small - img_min) / (img_max - img_min)
    else:
        img_normalized = img_small / 255.0

    if invert_brightness:
        indices = ((1.0 - img_normalized) * (num_chars - 1)).astype(int)
    else:
        indices = (img_normalized * (num_chars - 1)).astype(int)
    indices = np.clip(indices, 0, num_chars - 1)

    if not ansi_colors:
        return "\n".join("".join(chars[idx] for idx in row) for row in indices)

    cell_colors = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA).astype(np.float32)
    return ansi_text(indices, chars, apply_tint(cell_colors, tint_color))

def process_frame(frame, options):
    """
    Process a single frame (numpy array) into ASCII art.
    
    Args:
        frame: numpy array of shape (h, w, 3) - RGB image
        options: AsciiFrameOptions object containing processing parameters
    
    Returns:
        numpy array of shape (rows * char_h, cols * char_w, 3) - ASCII art image
    """
    h, w = frame.shape[:2]
    if options.swap_dims:
        h, w = w, h
    
    # Calculate grid dimensions
    cols = w // options.char_w
    rows = h // options.char_h
    
    shape_idx = None
    if is_mask_mode(options.mode):
        shape_idx = mask_indices(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), rows, cols,
                                 options.mode, options.invert_brightness)
    elif is_shape_mode(options.mode):
        shape_idx = shape_indices(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), rows, cols,
                                  options.mode, options.invert_brightness)
    
    if options.preserve_colors:
        # Preserve colors mode: skip grayscale and normalization
        # Resize RGB frame to grid size
        img_small_rgb = cv2.resize(frame, (cols, rows), interpolation=cv2.INTER_AREA)
        
        # Calculate brightness for character selection (but don't normalize)
        # Use luminance formula: 0.299*R + 0.587*G + 0.114*B
        img_brightness = (0.299 * img_small_rgb[:, :, 0] + 
                         0.587 * img_small_rgb[:, :, 1] + 
                         0.114 * img_small_rgb[:, :, 2])
        
        num_chars = options.num_chars if options.num_chars is not None else len(options.char_palette)
        
        # Map brightness directly to indices without normalization
        # Use full 0-255 range mapped to 0-(num_chars-1)
        if options.invert_brightness:
            indices = ((255.0 - img_brightness) / 255.0 * (num_chars - 1)).astype(int)
        else:
            indices = (img_brightness / 255.0 * (num_chars - 1)).astype(int)
        
        indices = np.clip(indices, 0, num_chars - 1)
        if shape_idx is not None:
            indices = shape_idx
        
        # Get selected characters
        tiled_chars = options.char_palette[indices]  # (rows, cols, char_h, char_w, 3)
        
        # Colorize characters based on original pixel colors
        bg_color_arr = np.array(options.bg_color, dtype=np.float32)
        fg_color_arr = np.array(options.fg_color, dtype=np.float32)
        
        # Expand sampled colors to match character dimensions
        cell_colors = img_small_rgb.astype(np.float32)  # (rows, cols, 3)
        cell_colors_expanded = cell_colors[:, :, np.newaxis, np.newaxis, :]  # (rows, cols, 1, 1, 3)
        
        # Create mask using luminance-based approach for better antialiasing handling
        # Convert character pixels to grayscale to determine character intensity
        tiled_chars_float = tiled_chars.astype(np.float32)
        
        # Calculate luminance of each pixel in the character
        char_luminance = (0.299 * tiled_chars_float[:, :, :, :, 0] + 
                         0.587 * tiled_chars_float[:, :, :, :, 1] + 
                         0.114 * tiled_chars_float[:, :, :, :, 2])
        
        # Calculate luminance of bg and fg colors
        bg_lum = 0.299 * bg_color_arr[0] + 0.587 * bg_color_arr[1] + 0.114 * bg_color_arr[2]
        fg_lum = 0.299 * fg_color_arr[0] + 0.587 * fg_color_arr[1] + 0.114 * fg_color_arr[2]
        
        # Create mask based on how close pixel luminance is to fg vs bg
        # Normalize to 0-1 range where 1 = fully foreground, 0 = fully background
        if abs(fg_lum - bg_lum) > 1e-6:
            fg_mask = np.clip((char_luminance - bg_lum) / (fg_lum - bg_lum), 0.0, 1.0)
        else:
            # If fg and bg have same luminance, use color distance instead
            char_diff_fg = np.sum((tiled_chars_float - fg_color_arr) ** 2, axis=-1)
            char_diff_bg = np.sum((tiled_chars_float - bg_color_arr) ** 2, axis=-1)
            total_diff = char_diff_fg + char_diff_bg
            fg_mask = np.where(total_diff > 1e-6, 1.0 - (char_diff_fg / total_diff), 0.5)
        
        fg_mask = fg_mask[:, :, :, :, np.newaxis]  # Add channel dimension
        
        # Apply tint if specified
        if options.tint_color is not None:
            tint_arr = np.array(options.tint_color, dtype=np.float32) / 255.0
            cell_colors_expanded = cell_colors_expanded * tint_arr
        
        # Apply color: blend sampled color with character based on mask
        # This preserves antialiasing and character shape
        tiled_chars = (cell_colors_expanded * fg_mask + 
                      bg_color_arr * (1.0 - fg_mask)).astype(np.uint8)
        
    else:
        # Original mode: Grayscale & Normalize
        img_gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        img_small = cv2.resize(img_gray, (cols, rows), interpolation=cv2.INTER_NEAREST)

        # Map pixels to Indices
        num_chars = options.num_chars if options.num_chars is not None else len(options.char_palette)
        
        # Normalize to 0-1 range using min/max to ensure full range is used
        img_min = img_small.min()
        img_max = img_small.max()
        if img_max > img_min:
            img_normalized = (img_small - img_min) / (img_max - img_min)
        else:
            img_normalized = img_small / 255.0
        
        if options.invert_brightness:
            indices = ((1.0 - img_normalized) * (num_chars - 1)).astype(int)
        else:
            indices = (img_normalized * (num_chars - 1)).astype(int)
        
        indices = np.clip(indices, 0, num_chars - 1)
        if shape_idx is not None:
            indices = shape_idx

        # The Magic Trick (Advanced Numpy Indexing)
        tiled_chars = options.char_palette[indices]

    # Stitching (Reshaping)
    # Swap axes to: (rows, char_h, cols, char_w, 3)
    tiled_chars = tiled_chars.swapaxes(1, 2)
    
    # Collapse the grid
    final_frame = tiled_chars.reshape(rows * options.char_h, cols * options.char_w, 3)
    
    return final_frame

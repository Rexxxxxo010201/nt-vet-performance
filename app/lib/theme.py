"""
Visual design system for the NT VET app: palette, the shared Plotly
template, and the chart_card layout helper.

Palette rationale
------------------
One highlight colour (ochre) carries the "this is the point" data-ink.
Blue is reserved only for target/reference markers, never for actual
delivery data, so the two accents never compete for the same meaning.
Orange and blue sit on opposite sides of the blue-yellow axis, which is
preserved under the common red-green colour vision deficiencies
(protanopia, deuteranopia), so this pairing stays distinguishable for
colour-blind readers. Hue alone is never the only cue though: pair this
palette with distinct marker shapes or line styles for target vs actual
(see chart-building code), and always add direct labels, since colour is
never load-bearing on its own.

Contrast (WCAG relative luminance, against white, checked at build time):
  text       #1F2933  ratio 14.76  (passes AA for any text size)
  blue       #2B6CB0  ratio  5.42  (passes AA for normal text)
  ochre      #A35A16  ratio  5.21  (passes AA for normal text, including
                                     white text set on an ochre fill -
                                     darkened from the original #B5651D,
                                     which was 4.34, just short of 4.5)
  grey_mid   #9AA0A6  ratio  2.64  (fails AA even for large text - use for
                                     non-text chart ink only: bar fills,
                                     axis lines, muted markers. Never set
                                     this as a text colour.)
  grey_light #D9DCE0  ratio  1.38  (decorative only: subtle fills, card
                                     borders, dividers. Never text.)
  grey_dark  #4B5563  ratio  7.56  (passes AA for any text size, including
                                     small text set over the blue/ochre
                                     table-cell tints - use where small
                                     grey text must stay readable over a
                                     coloured background.)
  grey_dot   #6B7280  ratio  4.83  (passes AA for normal text - a mid grey
                                     dark enough to read as a marker/line
                                     colour in its own right, between
                                     grey_mid's decorative-only tone and
                                     grey_dark's small-text tone.)

Because grey_mid cannot carry text accessibly, the chart_card caveat line
uses Streamlit's own muted caption styling (st.caption) rather than a
custom grey span, and any in-chart annotation text uses the full-contrast
text colour at a smaller size instead of a lighter grey.
"""

from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

OCHRE = "#A35A16"
GREY_MID = "#9AA0A6"
GREY_LIGHT = "#D9DCE0"
GREY_DARK = "#4B5563"
GREY_DOT = "#6B7280"
TEXT = "#1F2933"
BLUE = "#2B6CB0"
WHITE = "#FFFFFF"

# A light wash of ochre over white (15% ochre, 85% white), for highlighting
# a single row in a table without using ochre at full strength as a text
# or large-area colour.
OCHRE_LIGHT_TINT = "#F1E6DC"

FONT_FAMILY = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
)

TEMPLATE_NAME = "nt_vet"


def register_template():
    """Register the nt_vet Plotly template. Safe to call more than once."""
    template = go.layout.Template(
        layout=go.Layout(
            font=dict(family=FONT_FAMILY, size=14, color=TEXT),
            paper_bgcolor=WHITE,
            plot_bgcolor=WHITE,
            showlegend=False,
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=True,
                linecolor=GREY_MID,
                ticks="outside",
                tickcolor=GREY_MID,
                tickfont=dict(color=TEXT),
            ),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                showline=False,
                tickfont=dict(color=TEXT),
            ),
            colorway=[OCHRE, BLUE, GREY_MID],
        )
    )
    pio.templates[TEMPLATE_NAME] = template


register_template()

# Plotly.js config applied to every chart in the app: no mode bar (toolbar).
PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}


def apply_template(fig):
    """Apply the nt_vet template to a figure in place and return it.
    Also sets the one hover style used across the app: white background,
    13px, in the body text colour - applied here so every chart's hover
    looks the same without each chart module repeating it."""
    fig.update_layout(template=TEMPLATE_NAME)
    fig.update_layout(hoverlabel=dict(bgcolor=WHITE, font=dict(size=13, color=TEXT)))
    return fig


LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "ntg_logo.svg"
LOGO_ALT_TEXT = "Northern Territory Government"
LOGO_WIDTH_PX = 140


def render_logo():
    """Render the NTG logo at the very top of the page: left-aligned,
    about 140px wide, height scaled automatically from the SVG's own
    aspect ratio, with a 12px gap below it. Reads app/assets/ntg_logo.svg
    and embeds it inline - st.image does not reliably render SVG across
    Streamlit versions, and no remote URL is used. The file on disk is
    never altered; only the in-memory copy used for display gets a
    width/height style added to the root <svg> tag."""
    if not LOGO_PATH.exists():
        raise FileNotFoundError(f"render_logo: no file at {LOGO_PATH}.")
    svg_text = LOGO_PATH.read_text()
    if "<svg" not in svg_text:
        raise ValueError(f"render_logo: {LOGO_PATH} does not look like an SVG file.")
    styled_svg = svg_text.replace(
        "<svg",
        f'<svg role="img" aria-label="{LOGO_ALT_TEXT}" '
        f'style="width:{LOGO_WIDTH_PX}px;height:auto;display:block;"',
        1,
    )
    st.markdown(
        f'<div title="{LOGO_ALT_TEXT}" style="margin-bottom:12px;">{styled_svg}</div>',
        unsafe_allow_html=True,
    )


def configure_page(page_title):
    """Call once, as the first Streamlit command in every page script.
    Sets page config and caps content width at ~900px so the page reads
    like a document. On narrower (mobile) viewports the max-width simply
    never binds, so no separate mobile layout is needed."""
    st.set_page_config(page_title=page_title, layout="centered")
    st.markdown(
        """
        <style>
        .block-container { max-width: 900px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def chart_card(title, fig, caption, caveat=None, reading_aid=None, stats_line=None, takeaway=None):
    """Render one chart as a self-contained card: a declarative heading,
    an optional bold takeaway line, the chart itself, an optional one-line
    reading aid, a short plain-English caption, an optional demoted
    statistics line, and an optional small caveat line.

    title: the finished, data-driven sentence from titles.py - rendered as
        a heading, never typed by hand at the call site.
    fig: a Plotly figure. apply_template() is called on it here, so chart
        code doesn't need to remember to do it.
    caption: 2-3 sentences of plain English explaining what the chart shows.
    caveat: optional short grey line for a methodology note or limitation.
    reading_aid: optional one-line note directly under the chart, in
        normal text colour (not muted grey) at 13px, for example how to
        read a dot plot's dots and intervals.
    stats_line: optional small grey paragraph with the p-value or interval
        behind the caption, demoted below the plain-English claim.
    takeaway: optional bold one-line note directly above the chart, below
        the title, in normal text colour at 14px - a dot plot's one-line
        summary of how tightly its groups cluster.
    """
    st.markdown(f"#### {title}")
    if takeaway:
        st.markdown(f"<p style='color:{TEXT};font-size:14px;font-weight:bold;'>{takeaway}</p>", unsafe_allow_html=True)
    apply_template(fig)
    st.plotly_chart(fig, config=PLOTLY_CONFIG, width="stretch")
    if reading_aid:
        st.markdown(f"<p style='color:{TEXT};font-size:13px;'>{reading_aid}</p>", unsafe_allow_html=True)
    st.write(caption)
    if stats_line:
        st.caption(stats_line)
    if caveat:
        st.caption(caveat)


def action_card(priority, title, found, to_confirm, next_step, note=None, likely_explanation=None, stats_line=None):
    """One "So what" action card: a priority chip, a declarative title,
    then labelled blocks (what we found, an optional likely explanation to
    test, what to confirm, the next step). The card sits in a bordered
    container and never scrolls.

    priority: "Now" (ochre chip, white text) or "Next"/"Monitor" (grey chip).
    to_confirm: a list of up to four short items, shown as a bullet list.
    note: optional small grey line under the found block (for example, the
        count of contracts the figures cover).
    likely_explanation: an optional unproven idea plus the check that would
        test it, shown as its own labelled block right after found.
    stats_line: an optional small grey paragraph (13px, GREY_DOT) with the
        p-value or interval behind the found text, demoted below it."""
    chip_colour = OCHRE if priority == "Now" else GREY_DOT
    with st.container(border=True):
        st.markdown(
            f"<span style='background-color:{chip_colour};color:{WHITE};padding:2px 8px;"
            f"border-radius:4px;font-size:12px;font-weight:600;'>{priority}</span>",
            unsafe_allow_html=True,
        )
        st.markdown(f"#### {title}")
        st.markdown(f"**What we found.** {found}")
        if note:
            st.caption(note)
        if stats_line:
            st.markdown(f"<p style='color:{GREY_DOT};font-size:13px;'>{stats_line}</p>", unsafe_allow_html=True)
        if likely_explanation:
            st.markdown(f"**Likely explanation to test.** {likely_explanation}")
        st.markdown("**To confirm.**")
        st.markdown("\n".join(f"- {item}" for item in to_confirm))
        st.markdown(f"**Next step.** {next_step}")


def likely_explanation_note(text):
    """A 'Likely explanation to test: ...' line, with the 'Likely
    explanation to test' label in bold and the rest in normal text
    colour at 14px (not the muted small-grey caveat style). The text
    itself is unchanged; only the label is split out for styling."""
    label, sep, body = text.partition(":")
    if sep:
        st.markdown(f"<p style='color:{TEXT};font-size:14px;'><b>{label}:</b>{body}</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:{TEXT};font-size:14px;'>{text}</p>", unsafe_allow_html=True)

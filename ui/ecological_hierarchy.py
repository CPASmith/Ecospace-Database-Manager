"""Vue globale des règles écologiques, indépendante des occurrences individuelles."""
from collections import defaultdict
import json
import streamlit as st

FIELDS = ("tiering", "motility", "feeding", "size", "main_biomineralisation")
LABELS = {"tiering": "Tiering", "motility": "Motility", "feeding": "Feeding", "size": "Size", "main_biomineralisation": "Main biomineralisation"}


def _q(text):
    return json.dumps(str(text), ensure_ascii=False)


def _build_dot(contexts, dimensions, choices, selected, show_answers):
    lines = ["digraph Eco {", 'graph [rankdir=LR, bgcolor="transparent", pad="0.3", nodesep="0.24", ranksep="0.65", splines=polyline];',
             'node [fontname="Arial", fontsize=10, style="rounded,filled", shape=box, color="#7e93a2", fillcolor="#f0f5f8"];',
             'edge [color="#8797a4", arrowsize=0.55];']
    questions = defaultdict(lambda: defaultdict(set))
    for context_id, question, answer in dimensions:
        if question is not None:
            questions[context_id][str(question)].add(str(answer) if answer is not None else "(empty)")
    ctx_by_id = {r[0]: dict(zip(FIELDS, r[1:])) for r in contexts}
    needed = defaultdict(set)
    active = []
    for context_id, conditions in ctx_by_id.items():
        if context_id not in questions:
            continue
        if any(k not in selected for k, v in conditions.items() if v is not None):
            continue
        active.append((context_id, conditions))
        for key, val in conditions.items():
            if val is not None:
                needed[key].add(str(val))
    for key in selected:
        values = sorted(set(str(v) for v in choices.get(key, []) if v is not None) | needed[key], key=str.casefold)
        did = 'dim_' + key
        lines.append(f'{_q(did)} [label={_q(LABELS[key])}, fillcolor="#c7e7df", color="#388b79", penwidth=1.5];')
        for idx, val in enumerate(values):
            vid = f'val_{key}_{idx}'
            lines.append(f'{_q(vid)} [label={_q(val)}, fillcolor="#e9f5f0"];')
            lines.append(f'{_q(did)} -> {_q(vid)};')
    val_ids = {key: {val: f'val_{key}_{i}' for i, val in enumerate(sorted(set(str(v) for v in choices.get(key, []) if v is not None) | needed[key], key=str.casefold))} for key in selected}
    for context_id, conditions in active:
        requirements = [(k, str(v)) for k,v in conditions.items() if v is not None]
        cid = f'ctx_{context_id}'
        if len(requirements) > 1:
            lines.append(f'{_q(cid)} [label="AND", shape=diamond, style=filled, fillcolor="#fff1d6", color="#c99643"];')
            for key,val in requirements:
                if key in val_ids and val in val_ids[key]:
                    lines.append(f'{_q(val_ids[key][val])} -> {_q(cid)};')
        elif len(requirements) == 1:
            key,val = requirements[0]
            lines.append(f'{_q(cid)} [label="", shape=point, width=0.03];')
            if key in val_ids and val in val_ids[key]:
                lines.append(f'{_q(val_ids[key][val])} -> {_q(cid)};')
        else:
            lines.append(f'{_q(cid)} [label="Any ecological profile", shape=ellipse, fillcolor="#fff1d6"];')
        for j, (question, answers) in enumerate(sorted(questions[context_id].items())):
            qid = f'q_{context_id}_{j}'
            lines.append(f'{_q(qid)} [label={_q(question)}, fillcolor="#e9e5fa", color="#8c78b7"];')
            lines.append(f'{_q(cid)} -> {_q(qid)};')
            if show_answers:
                for a, answer in enumerate(sorted(answers, key=str.casefold)):
                    aid = f'a_{context_id}_{j}_{a}'
                    lines.append(f'{_q(aid)} [label={_q(answer)}, fillcolor="#f7f2ff", color="#b4a4cf"];')
                    lines.append(f'{_q(qid)} -> {_q(aid)};')
    lines.append('}')
    return "\n".join(lines), len(active), sum(len(questions[cid]) for cid,_ in active)


def show_full_ecological_hierarchy(conn, cursor):
    st.header("🌿 Ecological dimensions — complete hierarchy")
    st.caption("Structure des dimensions, conditions d'activation, questions et réponses possibles. Ce schéma représente les règles définies dans la base, pas les réponses des occurrences.")
    cursor.execute("SELECT id, tiering, motility, feeding, size, main_biomineralisation FROM contexts ORDER BY id")
    contexts = cursor.fetchall()
    cursor.execute("SELECT context_id, question, value FROM contextual_dimensions ORDER BY context_id, question, value")
    dimensions = cursor.fetchall()
    choices = {}
    for key in FIELDS:
        # Identifiants de colonnes provenant exclusivement de FIELDS (constante du code).
        cursor.execute(f'SELECT DISTINCT "{key}" FROM my_data WHERE "{key}" IS NOT NULL')
        choices[key] = [row[0] for row in cursor.fetchall()]
    for row in contexts:
        for key, value in zip(FIELDS, row[1:]):
            if value is not None:
                choices[key].append(value)
    selected = st.multiselect("Dimensions principales à afficher", list(FIELDS), default=list(FIELDS), format_func=lambda x: LABELS[x])
    show_answers = st.checkbox("Afficher toutes les réponses possibles", value=True)
    if not selected:
        st.info("Sélectionne au moins une dimension.")
        return
    dot, count_contexts, count_questions = _build_dot(contexts, dimensions, choices, selected, show_answers)
    st.caption(f"{count_contexts} contextes avec questions · {count_questions} questions contextuelles (par contexte).")
    st.graphviz_chart(dot, use_container_width=True)
    #st.download_button("⬇️ Télécharger le schéma (Graphviz DOT)", dot, file_name="ecological_hierarchy.dot", mime="text/vnd.graphviz")
    
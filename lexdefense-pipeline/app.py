from pathlib import Path
import tempfile

import streamlit as st

from lexdefense.pipeline.orchestrator import PipelineOrchestrator


def main():
    st.set_page_config(page_title="LexDefense Pipeline", layout="wide")
    st.title("LexDefense Pipeline")
    st.warning(
        "Este sistema genera borradores para revision humana. No sustituye el criterio profesional del abogado.",
    )

    orchestrator = PipelineOrchestrator()
    uploaded_files = st.file_uploader("Sube archivos del expediente", accept_multiple_files=True)
    client_role = st.selectbox(
        "Rol procesal",
        ["aseguradora_llamada_en_garantia", "distrito_demandado", "otro"],
    )

    if st.button("Ejecutar pipeline") and uploaded_files:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            input_dir = tmp_path / "input"
            run_dir = tmp_path / "run"
            input_dir.mkdir(parents=True, exist_ok=True)

            for uploaded in uploaded_files:
                (input_dir / uploaded.name).write_bytes(uploaded.getvalue())

            orchestrator.ingest(input_dir, run_dir)
            orchestrator.build_case(run_dir, client_role)
            orchestrator.generate_matrix(run_dir)
            orchestrator.draft(run_dir)
            orchestrator.audit(run_dir)
            status = orchestrator.export(run_dir, "md")

            st.success("Pipeline completado")
            st.json(status)
            st.code((run_dir / "draft_contestacion.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

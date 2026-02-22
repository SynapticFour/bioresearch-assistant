/*
 * BLAST Search — GA4GH WES compatible Nextflow workflow
 * Biocontainers: biocontainers/blast:2.14.0
 * Input: query_file (FASTA), database (nt/nr/custom), evalue, max_hits
 * Output: results.xml (BLAST XML), results.tsv, summary.json
 */

params.query_file = null
params.database = "nt"
params.evalue = 0.001
params.max_hits = 10
params.sequence_type = "auto"  // "nucleotide" | "protein" | "auto"
params.db_path = null          // optional: full path to BLAST DB; else params.database as name
params.outdir = "."

if (params.query_file == null || params.query_file == "") {
    error "query_file is required"
}

query = file(params.query_file, checkExists: true)
db_arg = params.db_path ?: params.database

process blast_search {
    tag "blast"
    publishDir(params.outdir, mode: "copy")
    input:
    path(q) from query
    output:
    path("results.xml")
    path("results.tsv")
    path("summary.json")
    container "biocontainers/blast:2.14.0"
    script:
    """
    set -e
    # Detect sequence type from first sequence (non-ACGTU -> protein)
    SEQ_TYPE="nucleotide"
    if [ "${params.sequence_type}" = "protein" ]; then
        SEQ_TYPE="protein"
    elif [ "${params.sequence_type}" = "auto" ]; then
        FIRST_SEQ=$(awk '/^>/ { getline; while (getline && !/^>/) seq=seq\$0 } END { print seq }' "${q}" | head -c 5000)
        if echo "$FIRST_SEQ" | grep -qE '[^ACGTUacgtuNn-]'; then
            SEQ_TYPE="protein"
        fi
    fi

    CMD="blastn"
    if [ "\$SEQ_TYPE" = "protein" ]; then CMD="blastp"; fi

    \$CMD -query "${q}" -db "${db_arg}" \\
        -outfmt 5 -out results.xml \\
        -evalue ${params.evalue} -max_target_seqs ${params.max_hits}

    \$CMD -query "${q}" -db "${db_arg}" \\
        -outfmt "6 qacc sacc pident length mismatch gapopen qstart qend sstart send evalue bitscore" \\
        -out results.tsv \\
        -evalue ${params.evalue} -max_target_seqs ${params.max_hits}

    python3 << 'PY'
    import json
    import xml.etree.ElementTree as ET
    root = ET.parse("results.xml").getroot()
    ns = {"b": "http://www.ncbi.nlm.nih.gov"}
    hits = root.findall(".//b:Hit", ns) or root.findall(".//Hit")
    hit_ids = []
    for h in hits[:20]:
        e = h.find("b:Hit_id", ns) or h.find("Hit_id")
        hit_ids.append(e.text if e is not None and e.text else "")
    prog = root.find("b:BlastOutput_program", ns) or root.find("BlastOutput_program")
    prog_text = prog.text if prog is not None and prog.text else "unknown"
    stats = {"num_hits": len(hits), "program": prog_text, "top_hit_ids": hit_ids}
    with open("summary.json", "w") as f:
        json.dump(stats, f, indent=2)
    PY
    """
}

workflow.onComplete {
    log.info "BLAST finished. results.xml, results.tsv, summary.json in ${params.outdir}"
}

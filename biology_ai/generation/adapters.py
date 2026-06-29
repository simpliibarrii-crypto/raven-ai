"""Generative biology AI adapters for openclinical-ai.

Each adapter wraps a generative biology model and provides a uniform interface
for the runtime. Adapters can be:

1. **Heuristic stubs** — for testing the architecture without real model weights
2. **ONNX-exported** — for portable inference across compute substrates
3. **Container-bundled** — for full-fidelity inference with the original model

Models supported:
- RFdiffusion (Baker lab) — backbone generation
- ProteinMPNN (Baker lab) — sequence design from backbone
- ESM-3 (EvolutionaryScale) — multi-modal protein generation
- Bindcraft (Baker lab) — binder design against target
- ProGen (Profluent/Salesforce) — protein language modelboleta**Critical:** Every adapter MUST pass generated sequences through biosecurity
screening (runtime/bio_security.py) before returning them. Per Science 2025,
synthesis-provider screening is insufficient against AI-redesigned sequences.
"""
from __future__ import annotations

import hashlib
import logging
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("openclinical.biology.generation")


@dataclass
class GenerationInput:
    """Input to a generative biology model."""
    constraints: dict[str, Any]
    model_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationOutput:
    """Output from a generative biology model — biologically valid + biosecurity-screened."""
    sequence: str
    sequence_type: str  # protein | rna | dna
    confidence: float  # 0-1 model self-reported confidence
    generation_id: str
    model_id: str
    model_version: str
    generation_timestamp: str
    generation_params: dict[str, Any]
    constraints_used: dict[str, Any]
    biosecurity: dict[str, Any]  # ScreeningResult dict
    metadata: dict[str, Any] = field(default_factory=dict)


# -- Base adapter -----------------------------------------------------------


class GenerativeBiologyAdapter:
    """Base class for generative biology model adapters.

    Subclasses implement _generate() (model-specific generation) and
    override run() to apply biosecurity screening.
    """

    model_id: str = ""
    model_version: str = "0.0.0"
    model_type: str = "generative-biology"
    description: str = ""
    sequence_type: str = "protein"  # default; subclasses override

    async def run(self, inputs: dict[str, Any], screener: Any) -> GenerationOutput:
        """Run generation + biosecurity screening.

        The screener argument is a BiosecurityScreener instance.
        """
        generation_id = str(uuid.uuid4())

        # 1. Call model-specific generation
        raw_sequence, confidence, metadata = await self._generate(inputs)

        # 2. Screen the generated sequence
        screening = screener.screen(raw_sequence, self.sequence_type)

        # 3. Build output
        return GenerationOutput(
            sequence=raw_sequence,
            sequence_type=self.sequence_type,
            confidence=confidence,
            generation_id=generation_id,
            model_id=self.model_id,
            model_version=self.model_version,
            generation_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            generation_params=inputs.get("model_params", {}),
            constraints_used=inputs.get("constraints", {}),
            biosecurity={
                "sequence_id": screening.sequence_id,
                "cleared": screening.cleared,
                "flags": screening.flags,
                "risk_score": screening.risk_score,
                "screening_timestamp": screening.screening_timestamp,
                "notes": screening.notes,
            },
            metadata=metadata,
        )

    async def _generate(self, inputs: dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Generate a sequence. Override in subclass."""
        raise NotImplementedError


# -- RFdiffusion (backbone generation) --------------------------------------


class RFdiffusionAdapter(GenerativeBiologyAdapter):
    """RFdiffusion — generative protein backbone design (Baker lab).

    Open source (BSD). Generates protein backbone coordinates from scratch or
    conditioned on a binding target. Produces a structure (PDB) that ProteinMPNN
    can then sequence-design from.

    Reference: Watson et al., Nature 2023 (https://www.nature.com/articles/s41586-023-06415-8)
    Source: https://github.com/RosettaCommons/RFdiffusion

    MVP: stub adapter. Production: container with RFdiffusion weights + GPU.
    """
    model_id = "rfdiffusion-backbone"
    model_version = "1.0.0"
    model_type = "generative-biology-structure"
    description = "Generative protein backbone design (Watson et al., Nature 2023). BSD open source."
    sequence_type = "structure"

    async def _generate(self, inputs: dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Generate a protein backbone (PDB-format string for MVP)."""
        constraints = inputs.get("constraints", {})
        n_residues = constraints.get("length", 100)
        n_residues = max(20, min(n_residues, 500))  # clamp

        # MVP: stub returns a fake PDB header (real model returns coordinates)
        pdb_stub = (
            f"HEADER    RFDIFFUSION BACKBONE STUB    {n_residues}-RESIDUE DESIGN\n"
            f"TITLE     OPENCLINICAL-AI MVP STUB\n"
            f"REMARK    THIS IS A STUB PDB FOR TESTING\n"
            f"REMARK    PRODUCTION WOULD CALL RFDIFFUSION IN A CONTAINER\n"
            f"REMARK    N_RESIDUES={n_residues}\n"
        )

        confidence = 0.85
        metadata = {
            "stub": True,
            "model_source": "github.com/RosettaCommons/RFdiffusion",
            "license": "BSD",
            "paper": "Watson et al., Nature 2023",
            "n_residues": n_residues,
            "format": "pdb-stub",
        }

        return pdb_stub, confidence, metadata


# -- ProteinMPNN (sequence design) ------------------------------------------


class ProteinMPNNAdapter(GenerativeBiologyAdapter):
    """ProteinMPNN — sequence design from backbone (Baker lab).

    Open source (BSD). Takes a protein backbone (PDB) and designs a sequence
    that folds to that backbone. Inverse folding.

    Reference: Dauparas et al., Science 2022 (https://www.science.org/doi/10.1126/science.add2187)
    Source: https://github.com/dauperez/ProteinMPNN

    MVP: stub adapter. Production: container with ProteinMPNN weights + GPU.
    """
    model_id = "proteinmpnn-inverse-fold"
    model_version = "1.0.0"
    model_type = "generative-biology-sequence"
    description = "Inverse folding — sequence design from backbone (Dauparas et al., Science 2022). BSD open source."
    sequence_type = "protein"

    # Standard amino acids
    AAs = "ACDEFGHIKLMNPQRSTVWY"

    async def _generate(self, inputs: dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Generate a protein sequence for a given backbone (MVP: stub)."""
        constraints = inputs.get("constraints", {})
        target_length = constraints.get("length", 100)
        target_length = max(10, min(target_length, 500))

        # MVP: stub — generates a plausible-looking sequence
        # Real ProteinMPNN would use the input PDB + a neural network
        random.seed(target_length)  # deterministic for testing
        sequence = "".join(random.choices(self.AAs, k=target_length))

        confidence = 0.78
        metadata = {
            "stub": True,
            "model_source": "github.com/dauperez/ProteinMPNN",
            "license": "BSD",
            "paper": "Dauparas et al., Science 2022",
            "length": target_length,
            "real_input_required": "PDB backbone coordinates",
        }

        return sequence, confidence, metadata


# -- ESM-3 (multi-modal protein generation) ---------------------------------


class ESM3Adapter(GenerativeBiologyAdapter):
    """ESM-3 — generative protein language model (EvolutionaryScale).

    Multi-modal: generates proteins conditioned on sequence, structure, and
    function. "Simulating 500 million years of evolution with a language model."

    Reference: Hayes et al., bioRxiv 2024 (https://www.biorxiv.org/content/10.1101/2024.07.01.599395v1)
    Source: https://github.com/evolutionaryscale/esm

    MVP: stub adapter. Production: container with ESM Cambrian weights + GPU.
    """
    model_id = "esm3-multimodal"
    model_version = "1.0.0"
    model_type = "generative-biology-multimodal"
    description = "Multi-modal protein language model (Hayes et al., 2024). Sequence + structure + function conditioning."
    sequence_type = "protein"

    AAs = "ACDEFGHIKLMNPQRSTVWY"

    async def _generate(self, inputs: dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Generate a protein conditioned on multi-modal constraints (MVP: stub)."""
        constraints = inputs.get("constraints", {})
        target_length = constraints.get("length", 150)
        target_length = max(20, min(target_length, 1024))

        # MVP: stub — sequence biased toward the constraint motif if provided
        seed_seq = ""
        motif = constraints.get("motif")
        if motif and re.match(r"^[ACDEFGHIKLMNPQRSTVWY]+$", motif):
            seed_seq = motif.upper()
            remaining = target_length - len(seed_seq)
            if remaining > 0:
                seed_seq += "".join(random.choices(self.AAs, k=remaining))
            else:
                seed_seq = seed_seq[:target_length]
        else:
            seed_seq = "".join(random.choices(self.AAs, k=target_length))

        confidence = 0.82
        metadata = {
            "stub": True,
            "model_source": "github.com/evolutionaryscale/esm",
            "license": "Apache 2.0 (ESM Cambrian)",
            "paper": "Hayes et al., bioRxiv 2024",
            "length": target_length,
            "motif_used": motif,
        }

        return seed_seq, confidence, metadata


# -- Bindcraft (binder design) ---------------------------------------------


class BindcraftAdapter(GenerativeBiologyAdapter):
    """Bindcraft — binder design against target (Baker lab).

    Open source. Designs a protein binder against a target protein structure.
    Hallmarks + RFdiffusion + ProteinMPNN pipeline.

    Source: https://github.com/martinpacesa/bindcraft

    MVP: stub adapter. Production: full Bindcraft pipeline.
    """
    model_id = "bindcraft-binder-design"
    model_version = "1.0.0"
    model_type = "generative-biology-binder"
    description = "Binder design against target protein structure. Pipeline: hallucination + RFdiffusion + ProteinMPNN + AlphaFold."
    sequence_type = "protein"

    AAs = "ACDEFGHIKLMNPQRSTVWY"

    async def _generate(self, inputs: dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Generate a binder sequence against target (MVP: stub)."""
        constraints = inputs.get("constraints", {})
        target_length = constraints.get("length", 80)
        target_length = max(40, min(target_length, 200))  # binders are typically 60-150 AA

        # MVP: stub — would do target-conditioned binder design
        random.seed(target_length * 7)  # deterministic
        sequence = "".join(random.choices(self.AAs, k=target_length))

        confidence = 0.75
        metadata = {
            "stub": True,
            "model_source": "github.com/martinpacesa/bindcraft",
            "license": "BSD",
            "pipeline": ["hallucination", "rfdiffusion", "proteinmpnn", "alphafold"],
            "length": target_length,
            "real_input_required": "target PDB + target binding site residues",
        }

        return sequence, confidence, metadata


# -- ProGen (protein LLM) --------------------------------------------------


class ProGenAdapter(GenerativeBiologyAdapter):
    """ProGen — protein language model (Profluent / Salesforce, open source).

    Control-tag-conditioned protein LLM. Generate proteins with specific
    functional tags (e.g. "lysozyme", "kinase").

    Reference: Madani et al., Nature Biotechnology 2023
    Source: https://github.com/salesforce/progen

    MVP: stub adapter. Production: container with ProGen weights + GPU.
    """
    model_id = "progen-protein-llm"
    model_version = "1.0.0"
    model_type = "generative-biology-sequence"
    description = "Control-tag-conditioned protein language model (Madani et al., 2023). Open source."
    sequence_type = "protein"

    AAs = "ACDEFGHIKLMNPQRSTVWY"

    async def _generate(self, inputs: dict[str, Any]) -> tuple[str, float, dict[str, Any]]:
        """Generate a protein conditioned on control tag (MVP: stub)."""
        constraints = inputs.get("constraints", {})
        target_length = constraints.get("length", 200)
        target_length = max(20, min(target_length, 800))

        # MVP: stub
        random.seed(hash(constraints.get("control_tag", "default")) % 1000)
        sequence = "".join(random.choices(self.AAs, k=target_length))

        confidence = 0.80
        metadata = {
            "stub": True,
            "model_source": "github.com/salesforce/progen",
            "license": "Apache 2.0",
            "paper": "Madani et al., Nature Biotechnology 2023",
            "length": target_length,
            "control_tag": constraints.get("control_tag", "default"),
        }

        return sequence, confidence, metadata


# -- Registry of biology AI adapters ----------------------------------------


BIOLOGY_GENERATION_ADAPTERS: dict[str, type[GenerativeBiologyAdapter]] = {
    "rfdiffusion-backbone": RFdiffusionAdapter,
    "proteinmpnn-inverse-fold": ProteinMPNNAdapter,
    "esm3-multimodal": ESM3Adapter,
    "bindcraft-binder-design": BindcraftAdapter,
    "progen-protein-llm": ProGenAdapter,
}


def get_generation_adapter(model_id: str) -> GenerativeBiologyAdapter | None:
    """Look up a generative biology adapter by model ID."""
    cls = BIOLOGY_GENERATION_ADAPTERS.get(model_id)
    if cls is None:
        return None
    return cls()
# Test Infrastructure & E2E Verification Methodology

## 1. Overview & Test Architecture

The MdSolids Trusses test infrastructure is engineered for complete, rigorous, and opaque-box end-to-end (E2E) verification of the structural mechanics engine, REST API service, and graphical reporting subsystem.

The test framework adheres to four core engineering principles:
1. **Opaque-Box Verification**: Tests interact strictly through public interfaces (REST API endpoints and public solver pipelines), validating observed behaviors against independent physical and mathematical ground truth.
2. **Dual-Method Independence**: Direct Stiffness Method (DSM) displacement formulations are cross-validated against an independent pure static equilibrium Method of Joints (MoJ) matrix solver without utilizing stiffness or displacements.
3. **Strict Physical Conservation**: Every stable structural solution is audited for global translational equilibrium ($\sum F_x = 0, \sum F_y = 0$), rotational equilibrium ($\sum M_O = 0$), and nodal vector closure ($\max \|\mathbf{r}_j\| < 10^{-6}$ kN).
4. **Deterministic Reproducibility & Zero Flakiness**: All test cases are completely self-contained, isolated, stateless, and execution-order independent.

```
                      ┌────────────────────────────────────────┐
                      │          E2E Test Runner               │
                      │   (python -m pytest tests/test_e2e.py) │
                      └──────────────────┬─────────────────────┘
                                         │
         ┌───────────────────────────────┼──────────────────────────────┐
         │                               │                              │
         ▼                               ▼                              ▼
 ┌───────────────┐              ┌─────────────────┐            ┌──────────────────┐
 │  HTTP REST    │              │   Full Model    │            │ Standalone HTML  │
 │  API Client   │              │   Pipeline      │            │ & SVG Engine     │
 │  (TestClient) │              │ (solve_payload) │            │ (render_report)  │
 └───────┬───────┘              └────────┬────────┘            └────────┬─────────┘
         │                               │                              │
         ▼                               ▼                              ▼
 ┌────────────────────────────────────────────────────────────────────────────────┐
 │                        Structural Domain Kernel                                │
 │  ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   ┌────────────────┐  │
 │  │ Model & Unit │   │ Direct Stiff │   │ Method of     │   │ Zero-Force &   │  │
 │  │ Conversion   │   │ Method (DSM) │   │ Joints (MoJ)  │   │ Determinacy    │  │
 │  └──────────────┘   └──────────────┘   └───────────────┘   └────────────────┘  │
 └────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Four-Tier Testing Methodology

The test suite is structured into four distinct, progressive tiers designed to validate every dimension of the system from isolated feature mechanics to complex real-world structural systems.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   TIER 4: REAL-WORLD SCENARIOS                         │
│  8 N2 Exam Benchmarks, 25-Member Pratt Bridge, Roof Wind/Snow Cases    │
├────────────────────────────────────────────────────────────────────────┤
│                 TIER 3: CROSS-FEATURE COMBINATIONS                     │
│  Pairwise Multi-axial Loads, Mixed Sections, Material Allowables       │
├────────────────────────────────────────────────────────────────────────┤
│                 TIER 2: BOUNDARY & CORNER CASES                        │
│  Singular Mechanisms, Slender Elements, Indeterminacy, Collinear Bars   │
├────────────────────────────────────────────────────────────────────────┤
│                 TIER 1: CORE FEATURE COVERAGE                          │
│  >=5 Tests per Core Feature: Grid, Supports, DSM, MoJ, Stress, Units   │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Tier 1: Feature Coverage (>=5 Tests per Core Feature)
Tier 1 ensures that every individual capability outlined in `PROJECT.md` operates with precision. Each feature is exercised by a minimum of 5 dedicated test cases:
1. **Grid Definition & Snapping**: Parsing parameters, discrete snapping, non-integer steps, boundary clamping, nearest-node priority hit testing.
2. **Member Geometry & Connectivity**: Length computation ($L = \sqrt{\Delta x^2 + \Delta y^2}$), directional cosines ($c, s$), quadrant orientation, and connectivity.
3. **Standard Supports**: Pin (2 restraints), Roller Y (1 vertical restraint), Roller X (1 horizontal restraint), Free nodes, and support alias normalization.
4. **Nodal Point Loads**: Pure vertical, pure horizontal, inclined, multiple simultaneous loads, and nodal superposition.
5. **Force Classification**: Tension ($N > 0$), Compression ($N < 0$), and Zero-Force ($N = 0$) classification, plus summary statistics.
6. **Support Reaction Equilibrium**: Static equilibrium closure against analytical reactions on symmetric, asymmetric, horizontal, and vertical roller constraints.
7. **Direct Stiffness Method (DSM)**: Restrained DOF boundary enforcement, deformation symmetry, linear scaling with force, inverse scaling with $EA$, and stiffness matrix symmetry ($K = K^T$).
8. **Method of Joints Cross-Validation**: Dual-engine cross-checks on triangulated, Warren, Pratt, and irregular trusses, plus graceful non-applicability on indeterminate trusses.
9. **Global & Nodal Static Equilibrium**: Residual verification for $\sum F_x$, $\sum F_y$, $\sum M_{(0,0)}$, and worst nodal vector closure.
10. **Geometric Zero-Force Rules**: Analytical rules R1 (1 bar), R2 (2 non-collinear bars), R3 (3 bars with 2 collinear), and suppression under applied loads/supports.
11. **Static Determinacy Analysis**: Degree $g = b + r - 2n$ calculation, isostatic ($g = 0$), hypostatic ($g < 0$), indeterminate ($g > 0$).
12. **Mechanism & Instability Detection**: Spectral decomposition of $K_{ff}$, zero eigenvalue identification ($\lambda \le 10^{-10} \lambda_{\max}$), and identification of unstable DOFs.
13. **Normal Stress Analysis**: $\sigma = (N \times 1000) / A$ in MPa, tensile/compressive identification, critical stress identification, and missing area handling.
14. **Reverse Section Sizing**: Required area $A_{\text{req}} = (|N| \times 1000) / \sigma_{\text{adm}}$, distinct tension/compression limits, utilisation ratio, and governing section.
15. **Engineering Unit Conversions**: Seamless transformation between SI (kN, N, m, mm, MPa) and Imperial (kip, lbf, ft, in, ksi) on system boundaries.
16. **Preset Library & Model Serialization**: Complete roundtrip JSON serialization, retrieval of 12 preset metadata, and 404 error handling.
17. **Technical Report Generation**: Clean A4 printable HTML reports, embedded high-DPI SVG diagrams, and graceful error summaries for unresolvable trusses.

### 2.2 Tier 2: Boundary & Corner Cases (>=5 Tests per Feature Domain)
Tier 2 stress-tests numerical stability and error resilience under extreme geometric and topological edge cases:
1. **Extreme Geometry Ratios**: Slender members ($L/r \to \infty$), ultra-stiff elements, extreme aspect ratios (1:100 span/depth), tall slender towers, and stiffness contrasts ($10^6:1$).
2. **Right-Angle Triangles & Asymmetric Loads**: 30-60-90 and 45-45-90 triangles, anti-symmetric loads, skewed overhangs.
3. **Zero-Load Trusses**: Trivial zero loading returning identically zero forces, zero reactions, zero displacements, and clean equilibrium.
4. **Multiple Collinear Members**: Bottom chords, collinear load transfers, collinearity warnings, and vertical tower columns.
5. **Highly Indeterminate Trusses**: Multiple redundant diagonal ties ($g \ge 2$), multi-span continuous supports, hyperstatic force redistribution.
6. **Singular Mechanisms & Hypostatic Trusses**: 4-bar unbraced linkages, unconstrained bodies, horizontal collinear mechanisms returning structured error payloads (`"mechanism"`, `"hypostatic"`) without process crashes.
7. **Invalid Input Rejection**: Rejection of zero-length elements, duplicated reverse bars, non-positive $EA$, negative section areas, and unlinked nodes.

### 2.3 Tier 3: Cross-Feature Combinations (Pairwise Integration)
Tier 3 explores pairwise multi-domain interactions:
1. Multi-axial loads ($F_x \ne 0, F_y \ne 0$) acting concurrently on indeterminate trusses.
2. Multi-bay Warren and Pratt trusses comparing pin vs roller_x boundary conditions.
3. Trusses combining mixed cross-sections, materials, and distinct tension/compression allowable stresses.
4. Multi-load combinations that activate and deactivate zero-force members.
5. End-to-end full lifecycle roundtrip: Input JSON -> Unit conversion -> DSM -> MoJ -> Stress Sizing -> HTML Report -> SVG rendering.

### 2.4 Tier 4: Real-World Application Scenarios
Tier 4 executes complete end-to-end validation against the official N2 course benchmark problems:
1. **Case 01 (`01-triangulo`)**: Canonical 3-bar analytical reference.
2. **Case 02 (`02-telhado-pratt`)**: 8-node, 13-bar Pratt roof truss with tributary gravity loading and R3 zero-force members.
3. **Case 03 (`03-warren`)**: 7-node, 11-bar symmetric Warren bridge truss.
4. **Case 04 (`04-pratt-vento`)**: 8-node, 13-bar Pratt truss under lateral wind load.
5. **Case 05 (`05-forca-zero-T`)**: 4-node panel verifying rule R2 and Ritter section cross-checks.
6. **Case 06 (`06-forca-zero-R3`)**: 4-node truss verifying rule R3.
7. **Case 07 (`07-geometria-irregular`)**: Non-orthogonal truss with oblique loads.
8. **Case 08 (`08-hiperestatica`)**: Square frame with cross-bracing ($g = 1$).
9. **Case 12 (`12-pratt-grande`)**: Large 14-node, 25-bar Pratt bridge truss.
10. **Combined Roof Snow & Wind Case**: Reversal of tension and compression under combined uplift and gravity actions.

---

## 3. Execution Commands & Test Runner

The entire test suite is orchestrated through `pytest`.

### 3.1 Standard Test Execution
To execute the complete E2E test suite with verbose output:
```powershell
python -m pytest tests/test_e2e.py -v
```

### 3.2 Tier-Specific Filtering
To run specific tiers via pytest keyword matching:
```powershell
# Run Tier 1 only
python -m pytest tests/test_e2e.py -k "tier1" -v

# Run Tier 2 only
python -m pytest tests/test_e2e.py -k "tier2" -v

# Run Tier 3 only
python -m pytest tests/test_e2e.py -k "tier3" -v

# Run Tier 4 only
python -m pytest tests/test_e2e.py -k "tier4" -v
```

### 3.3 Running the Full Suite (Unit + Integration + E2E)
```powershell
python -m pytest -v
```

---

## 4. Mathematical Tolerances & Acceptance Thresholds

| Metric | Verification Equation | Tolerance Threshold |
|---|---|---|
| **Global Equilibrium $\sum F_x$** | $|\sum F_{jx}^{\text{ext}} + \sum R_{kx}|$ | $\le 10^{-6} \times \max(1, \max |N|)$ kN |
| **Global Equilibrium $\sum F_y$** | $|\sum F_{jy}^{\text{ext}} + \sum R_{ky}|$ | $\le 10^{-6} \times \max(1, \max |N|)$ kN |
| **Global Equilibrium $\sum M_O$** | $|\sum (x_j F_{jy} - y_j F_{jx}) + \sum (x_k R_{ky} - y_k R_{kx})|$ | $\le 10^{-5} \times \max(1, \max |N|)$ kN·m |
| **Nodal Equilibrium Vector** | $\max_j \|\sum_{e} N_e \hat{n}_{je} + \mathbf{F}_j^{\text{ext}} + \mathbf{R}_j\|$ | $\le 10^{-6} \times \max(1, \max |N|)$ kN |
| **Method of Joints Discrepancy**| $\max_e |N_e^{\text{DSM}} - N_e^{\text{MoJ}}|$ | $\le 10^{-7} \times \max(1, \max |N|)$ kN |
| **Zero-Force Member Identification** | $|N_e| \le \text{tol}$ | $\le 10^{-7} \times \max(1, \max |N|)$ kN |
| **Spectral Mechanism Threshold** | $\lambda_k(\mathbf{K}_{ff}) \le \text{tol}_{\text{rel}} \cdot \max |\lambda|$ | $\text{tol}_{\text{rel}} = 10^{-10}$ |
| **Stress Calculation** | $\sigma = (N \times 1000) / A$ | Relative error $\le 10^{-6}$ |
| **Section Sizing** | $A_{\text{req}} = (|N| \times 1000) / \sigma_{\text{adm}}$ | Relative error $\le 10^{-6}$ |
| **Determinacy Index** | $g = b + r - 2n$ | Exact integer identity |

---

## 5. Test Code Organization

All E2E tests reside in `tests/test_e2e.py`, structured into distinct test classes:
- `TestTier1CoreFeatures`: All 17 core features with $\ge 5$ tests each.
- `TestTier2BoundaryCases`: All 7 boundary/corner domains with $\ge 5$ tests each.
- `TestTier3CrossFeatureCombinations`: Pairwise multi-axial, multi-bay, mixed-material scenarios.
- `TestTier4RealWorldScenarios`: Full benchmark verification of N2 Exam problems 01-08, bridge case 12, and combined environmental roof load cases.

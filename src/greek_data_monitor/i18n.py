"""Lightweight English/Greek UI localization for the Streamlit dashboard."""

from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any


_GREEK = False
_INSTALLED = False


TRANSLATIONS = {
    # Navigation and common controls
    "Navigation": "Πλοήγηση",
    "📌 Overview": "📌 Επισκόπηση",
    "🔍 Explore Data": "🔍 Εξερεύνηση δεδομένων",
    "🇪🇺 Greece in Context": "🇪🇺 Η Ελλάδα στο ευρωπαϊκό πλαίσιο",
    "🏛️ Fiscal & Debt Surveillance": "🏛️ Δημοσιονομική εποπτεία και χρέος",
    "🔬 Cross-Series Analysis & Lab": "🔬 Ανάλυση δεικτών και εργαστήριο",
    "🛡️ Data Quality & Freshness": "🛡️ Ποιότητα και επικαιρότητα δεδομένων",
    "📑 Audit Reports & Data Export": "📑 Εκθέσεις ελέγχου και εξαγωγή δεδομένων",
    "📈 Greece: Progress & Challenges": "📈 Η πορεία της Ελλάδας: πρόοδος και προκλήσεις",
    "ℹ️ Sources & Methodology": "ℹ️ Πηγές και μεθοδολογία",
    "Language / Γλώσσα": "Γλώσσα / Language",
    "English": "English",
    "Ελληνικά": "Ελληνικά",
    "⚙️ Settings & Database": "⚙️ Ρυθμίσεις και βάση δεδομένων",
    "Database URL": "Διεύθυνση βάσης δεδομένων",
    "HTTP Timeout (seconds)": "Χρονικό όριο HTTP (δευτερόλεπτα)",
    "### 🔄 Ingestion & Refresh": "### 🔄 Εισαγωγή και ανανέωση δεδομένων",
    "🚀 Sync All Indicators (19)": "🚀 Συγχρονισμός όλων των δεικτών (19)",
    "🚀 Run Initial Sync Now": "🚀 Έναρξη αρχικού συγχρονισμού",
    "Fetch and validate all catalog indicators independently.": "Λήψη και ανεξάρτητος έλεγχος όλων των δεικτών του καταλόγου.",
    "Click **'🚀 Sync All Indicators'** in the sidebar to perform the initial ingestion of official data from Eurostat.": "Επιλέξτε **«🚀 Συγχρονισμός όλων των δεικτών»** από την πλαϊνή στήλη για να γίνει η αρχική λήψη επίσημων στοιχείων από τη Eurostat.",
    "Database contains no stored observations yet.": "Δεν υπάρχουν ακόμη αποθηκευμένες παρατηρήσεις στη βάση δεδομένων.",
    "### 🇬🇷 Greece Data Analyst": "### 🇬🇷 Αναλυτής Δεδομένων Ελλάδας",
    "Multi-Topic Official Data Analysis for Greece": "Ανάλυση επίσημων δεδομένων της Ελλάδας σε πολλούς τομείς",
    "Multi-Topic Official Public Data Surveillance for Greece": "Παρακολούθηση επίσημων δημόσιων δεδομένων για την Ελλάδα σε πολλούς τομείς",
    "Multi-Topic Official Public Data Surveillance for Greece.": "Παρακολούθηση επίσημων δημόσιων δεδομένων για την Ελλάδα σε πολλούς τομείς.",
    "off": "Ανενεργό",
    "primary": "Κύριο",

    # Page titles and summaries
    "<div class=\"brand-title\">🇬🇷 Greece Overview</div>": "<div class=\"brand-title\">🇬🇷 Επισκόπηση της Ελλάδας</div>",
    "<div class=\"brand-title\">🇬🇷 Greece Data Analyst</div>": "<div class=\"brand-title\">🇬🇷 Αναλυτής Δεδομένων Ελλάδας</div>",
    "<div class=\"brand-title\">🔍 Data Explorer & Indicator Analysis</div>": "<div class=\"brand-title\">🔍 Εξερεύνηση δεδομένων και ανάλυση δεικτών</div>",
    "<div class=\"brand-title\">🇪🇺 Greece in Context: International Benchmarks</div>": "<div class=\"brand-title\">🇪🇺 Η Ελλάδα στο πλαίσιο διεθνών συγκρίσεων</div>",
    "<div class=\"brand-title\">🏛️ Sovereign Debt & Fiscal Surveillance</div>": "<div class=\"brand-title\">🏛️ Δημόσιο χρέος και δημοσιονομική εποπτεία</div>",
    "<div class=\"brand-title\">🔬 Cross-Series Analysis & Macroeconomic Lab</div>": "<div class=\"brand-title\">🔬 Διασειριακή ανάλυση και μακροοικονομικό εργαστήριο</div>",
    "<div class=\"brand-title\">🛡️ Data Quality & Freshness Surveillance</div>": "<div class=\"brand-title\">🛡️ Έλεγχος ποιότητας και επικαιρότητας δεδομένων</div>",
    "<div class=\"brand-title\">📑 Audit Reports & Data Export Center</div>": "<div class=\"brand-title\">📑 Εκθέσεις ελέγχου και εξαγωγή δεδομένων</div>",
    "<div class=\"brand-title\">ℹ️ Sources, Methodology & Data Architecture</div>": "<div class=\"brand-title\">ℹ️ Πηγές, μεθοδολογία και αρχιτεκτονική δεδομένων</div>",
    "<div class=\"brand-title\">ℹ️ Sources & Methodology</div>": "<div class=\"brand-title\">ℹ️ Πηγές και μεθοδολογία</div>",
    "<div class=\"brand-subtitle\">Genuinely multi-topic public data surveillance for Greece</div>": "<div class=\"brand-subtitle\">Παρακολούθηση δημόσιων δεδομένων για την Ελλάδα σε πολλούς τομείς</div>",
    "<div class=\"brand-subtitle\">Cross-topic statistical surveillance across the Greek economy, society, energy, tourism, housing, and finance.</div>": "<div class=\"brand-subtitle\">Στατιστική παρακολούθηση της ελληνικής οικονομίας, κοινωνίας, ενέργειας, τουρισμού, στέγασης και χρηματοοικονομικών.</div>",
    "<div class=\"brand-subtitle\">Browse, search, analyze, and export verified time-series data across all monitored Greek statistical domains. Compare indicators safely with unit scale validation.</div>": "<div class=\"brand-subtitle\">Περιηγηθείτε, αναζητήστε, αναλύστε και εξαγάγετε ελεγμένα χρονοσειριακά δεδομένα. Συγκρίνετε δείκτες με έλεγχο μονάδων μέτρησης.</div>",
    "<div class=\"brand-subtitle\">Benchmark Greece against the EU-27 European Union average and peer Mediterranean and European economies (Germany, Italy, Spain, Portugal, Cyprus) using harmonized official Eurostat series.</div>": "<div class=\"brand-subtitle\">Συγκρίνετε την Ελλάδα με τον μέσο όρο της ΕΕ-27 και με ευρωπαϊκές και μεσογειακές οικονομίες (Γερμανία, Ιταλία, Ισπανία, Πορτογαλία, Κύπρο) βάσει εναρμονισμένων επίσημων σειρών της Eurostat.</div>",
    "<div class=\"brand-subtitle\">Empirical correlation matrices, bivariate regression modeling, and unit-scale normalized comparisons across official Greek time-series.</div>": "<div class=\"brand-subtitle\">Εμπειρικοί πίνακες συσχέτισης, διμεταβλητή παλινδρόμηση και κανονικοποιημένες συγκρίσεις επίσημων ελληνικών χρονοσειρών.</div>",
    "<div class=\"brand-subtitle\">Download machine-readable public datasets, generate statistical quality reports, and inspect retroactive data revisions between official ingestion runs.</div>": "<div class=\"brand-subtitle\">Κατεβάστε δημόσια δεδομένα σε μηχαναγνώσιμη μορφή, δημιουργήστε αναφορές ποιότητας και εξετάστε αναθεωρήσεις μεταξύ επίσημων λήψεων.</div>",
    "<div class=\"brand-subtitle\">Independent verification of completeness, timeliness, historical revisions, and anomaly detection. Separated quality findings from country statistics to ensure complete auditing transparency.</div>": "<div class=\"brand-subtitle\">Ανεξάρτητος έλεγχος πληρότητας, επικαιρότητας, ιστορικών αναθεωρήσεων και ανωμαλιών. Τα ευρήματα ποιότητας διαχωρίζονται από τα στατιστικά στοιχεία της χώρας.</div>",
    "<div class=\"brand-subtitle\">Specialized surveillance of Greece's sovereign debt trajectory, post-pandemic deleveraging dynamics, European fiscal governance rules (Maastricht criteria), and sovereign bond yield normalization.</div>": "<div class=\"brand-subtitle\">Παρακολούθηση της πορείας του δημόσιου χρέους, της απομείωσης μετά την πανδημία, των ευρωπαϊκών δημοσιονομικών κανόνων (κριτήρια του Μάαστριχτ) και των αποδόσεων ομολόγων.</div>",
    "<div class=\"brand-subtitle\">Complete transparency regarding official data sources, API endpoints, classification standards, known limitations, and the pipeline architecture. Zero invented or placeholder observations.</div>": "<div class=\"brand-subtitle\">Πλήρης διαφάνεια για τις επίσημες πηγές, τα API, τα πρότυπα ταξινόμησης, τους γνωστούς περιορισμούς και τη ροή δεδομένων. Δεν χρησιμοποιούνται επινοημένες ή ενδεικτικές παρατηρήσεις.</div>",

    # Overview and shared indicator labels
    "Catalog Indicators": "Δείκτες καταλόγου",
    "Indicators with Data": "Δείκτες με δεδομένα",
    "Stored Observations": "Αποθηκευμένες παρατηρήσεις",
    "Latest Reference Year": "Τελευταίο έτος αναφοράς",
    "Latest Value": "Τελευταία τιμή",
    "Reference Period": "Περίοδος αναφοράς",
    "Measurement Unit": "Μονάδα μέτρησης",
    "Official Authority": "Επίσημη αρχή",
    "Historical Records": "Ιστορικές εγγραφές",
    "Annual Series": "Ετήσιες σειρές",
    "6 Domains": "6 τομείς",
    "All Topics": "Όλοι οι τομείς",
    "All Sources": "Όλες οι πηγές",
    "Topic": "Τομέας",
    "Source Authority": "Αρμόδια πηγή",
    "Official Authority": "Επίσημη αρχή",
    "Source Authority": "Αρμόδια πηγή",
    "Official Source": "Επίσημη πηγή",
    "Official Authority": "Επίσημη αρχή",
    "Reference Period": "Περίοδος αναφοράς",
    "Latest Reference Year": "Τελευταίο έτος αναφοράς",
    "Domain Topic Filter": "Φίλτρο τομέα",
    "View Format": "Μορφή προβολής",
    "Headline Cards (9)": "Κύριοι δείκτες (9)",
    "All Indicators Grid (19)": "Όλοι οι δείκτες (19)",
    "Compact Table": "Συνοπτικός πίνακας",
    "Search by name, topic, dataset code...": "Αναζήτηση ονόματος, τομέα ή κωδικού συνόλου δεδομένων...",
    "Search Catalog": "Αναζήτηση καταλόγου",
    "🔎 Search Catalog": "🔎 Αναζήτηση καταλόγου",
    "Filter Catalog Table": "Φιλτράρισμα καταλόγου",
    "Filter Period Range": "Φιλτράρισμα περιόδου",
    "Select Active Indicator to Inspect": "Επιλέξτε δείκτη για εξέταση",
    "Primary Indicator (A)": "Κύριος δείκτης (A)",
    "Comparison Indicator (B)": "Συγκριτικός δείκτης (B)",
    "Select Benchmark Indicator": "Επιλέξτε δείκτη σύγκρισης",
    "Select Economies to Compare": "Επιλέξτε οικονομίες για σύγκριση",
    "Time Period": "Χρονική περίοδος",
    "Stored Observations": "Αποθηκευμένες παρατηρήσεις",
    "Latest": "Τελευταία τιμή",
    "Previous year": "Προηγούμενο έτος",
    "Direction": "Κατεύθυνση",
    "How to interpret it": "Ερμηνεία",
    "Latest Value": "Τελευταία τιμή",
    "Unit": "Μονάδα",
    "Frequency": "Συχνότητα",
    "Indicator": "Δείκτης",
    "Dataset Code": "Κωδικός συνόλου δεδομένων",
    "SDMX Series Key": "Κλειδί σειράς SDMX",
    "Direct Portal URL": "Άμεσος σύνδεσμος πηγής",
    "Coverage Start Year": "Έτος έναρξης κάλυψης",
    "Official Authority": "Επίσημη αρχή",
    "Source Authority": "Αρμόδια πηγή",
    "Description": "Περιγραφή",
    "Methodology Standard": "Μεθοδολογικό πρότυπο",
    "Known Limitations & Breaks": "Γνωστοί περιορισμοί και ασυνέχειες",
    "Direct API Endpoint": "Άμεσο σημείο πρόσβασης API",
    "Select Indicator for Detailed Methodology & Dimensions": "Επιλέξτε δείκτη για μεθοδολογία και διαστάσεις",
    "Select Indicator for API Wire Details": "Επιλέξτε δείκτη για λεπτομέρειες API",
    "Select Indicator to Export": "Επιλέξτε δείκτη για εξαγωγή",
    "Select Indicator for Formal Audit": "Επιλέξτε δείκτη για επίσημο έλεγχο",
    "Select Series to Audit": "Επιλέξτε σειρά για έλεγχο",
    "Select Series to Audit Revisions": "Επιλέξτε σειρά για έλεγχο αναθεωρήσεων",
    "Select Independent Variable (X-axis)": "Επιλέξτε ανεξάρτητη μεταβλητή (άξονας X)",
    "Select Dependent Variable (Y-axis)": "Επιλέξτε εξαρτημένη μεταβλητή (άξονας Y)",
    "Select Series A": "Επιλέξτε σειρά A",
    "Select Series B": "Επιλέξτε σειρά B",
    "Baseline Run (Earlier)": "Αρχική εκτέλεση (παλαιότερη)",
    "Comparison Run (Later)": "Συγκριτική εκτέλεση (νεότερη)",
    "Domain Topic Filter": "Φίλτρο τομέα",
    "Export Scope": "Εύρος εξαγωγής",
    "All 19 Indicators Consolidated": "Και οι 19 δείκτες μαζί",
    "Single Selected Indicator": "Ένας επιλεγμένος δείκτης",
    "Overlay Historical Milestones": "Εμφάνιση ιστορικών οροσήμων",
    "View Rendered Report Preview": "Προβολή προεπισκόπησης αναφοράς",
    "Export official time-series observations in CSV or JSON formats for downstream econometric modeling, policy research, or auditing.": "Εξαγωγή επίσημων χρονοσειριακών παρατηρήσεων σε CSV ή JSON για οικονομετρική ανάλυση, έρευνα πολιτικής ή έλεγχο.",

    # Page section headings
    "### 📈 Domain Trend Trajectories": "### 📈 Τάσεις ανά τομέα",
    "### 📈 Historical Multi-Country Trajectory": "### 📈 Ιστορική πορεία χωρών",
    "### ⚡ Notable Recent Movements": "### ⚡ Σημαντικές πρόσφατες μεταβολές",
    "### ⚖️ Safe Indicator Comparison Tool": "### ⚖️ Ασφαλής σύγκριση δεικτών",
    "### ⚖️ Safe Unit-Scale Comparison Lab": "### ⚖️ Εργαστήριο σύγκρισης μονάδων",
    "### 🔬 In-Depth Quality Audit & Scorecard": "### 🔬 Αναλυτικός έλεγχος και βαθμολογία ποιότητας",
    "### 📚 Official Indicator Catalog Directory": "### 📚 Κατάλογος επίσημων δεικτών",
    "### 🔬 Indicator Methodology Deep Dive": "### 🔬 Αναλυτική μεθοδολογία δείκτη",
    "### ⚠️ Documented Scope Limitations & Excluded Topics": "### ⚠️ Περιορισμοί κάλυψης και εξαιρούμενοι τομείς",
    "### 📋 Observations Data Table & Export": "### 📋 Πίνακας παρατηρήσεων και εξαγωγή",
    "### 📋 Comparative Observations Matrix & Disclosures": "### 📋 Συγκριτικός πίνακας παρατηρήσεων και γνωστοποιήσεις",
    "### 📋 Quality Findings Audit Log": "### 📋 Καταγραφή ευρημάτων ποιότητας",
    "### 📡 Source Checks & Retrieval Age": "### 📡 Έλεγχοι πηγών και χρόνος λήψης",
    "### 🔄 Historical Revision Detection between Runs": "### 🔄 Εντοπισμός ιστορικών αναθεωρήσεων μεταξύ εκτελέσεων",
    "### 🏗️ Data Architecture & Pipeline Resilience": "### 🏗️ Αρχιτεκτονική δεδομένων και ανθεκτικότητα ροής",
    "### 🔗 Developer & Researcher Wire API Reference": "### 🔗 Αναφορά API για προγραμματιστές και ερευνητές",
    "### 🧮 Multi-Indicator Pearson Correlation Matrix": "### 🧮 Πίνακας συσχέτισης Pearson πολλών δεικτών",
    "### 📐 Bivariate Regression & Scatter Plot": "### 📐 Διμεταβλητή παλινδρόμηση και διάγραμμα διασποράς",
    "### ❄️ Macroeconomic Denominator & Snowball Dynamics": "### ❄️ Μακροοικονομικός παρονομαστής και δυναμική χιονοστιβάδας",
    "### ⚖️ European Fiscal Governance & Surveillance Rulebook": "### ⚖️ Ευρωπαϊκό πλαίσιο δημοσιονομικής διακυβέρνησης και εποπτείας",
    "### 📉 10-Year Sovereign Benchmark Yield Normalization": "### 📉 Κανονικοποίηση απόδοσης 10ετούς κρατικού ομολόγου",
    "### 📈 Sovereign Debt-to-GDP Trajectory & Historical Crisis Milestones": "### 📈 Πορεία χρέους προς ΑΕΠ και ιστορικά ορόσημα κρίσεων",
    "#### Preview Data": "#### Προεπισκόπηση δεδομένων",
    "#### Reproducible Python Snippet": "#### Αναπαραγώγιμο απόσπασμα Python",
    "### 📄 Formal Quality Audit Report Generator": "### 📄 Δημιουργία επίσημης αναφοράς ελέγχου ποιότητας",
    "### 📄 Download Formal Quality Audit Report": "### 📄 Λήψη επίσημης αναφοράς ελέγχου ποιότητας",
    "### 📥 Machine-Readable Data Export": "### 📥 Εξαγωγή δεδομένων σε μηχαναγνώσιμη μορφή",
    "### 🔍 Search Catalog": "### 🔍 Αναζήτηση στον κατάλογο",
    "### 📚 Indicator Catalog": "### 📚 Κατάλογος δεικτών",
    "### 📊 Overview": "### 📊 Επισκόπηση",
    "### 📊 Latest Values": "### 📊 Τελευταίες τιμές",
    "### 📉 Trend Analysis": "### 📉 Ανάλυση τάσεων",
    "### 🧭 What Changed": "### 🧭 Τι άλλαξε",
    "### 🧪 Quality Findings": "### 🧪 Ευρήματα ποιότητας",
    "### 📤 Export": "### 📤 Εξαγωγή",
    "### 📊 Comparative Benchmark": "### 📊 Συγκριτικά στοιχεία",
    "### 🌍 Country Comparison": "### 🌍 Σύγκριση χωρών",
    "### 📉 Debt Sustainability": "### 📉 Βιωσιμότητα χρέους",
    "### 📊 Fiscal Indicators": "### 📊 Δημοσιονομικοί δείκτες",
    "### 🛠️ Data Quality Rules": "### 🛠️ Κανόνες ποιότητας δεδομένων",
    "### 🔎 Revision Audit": "### 🔎 Έλεγχος αναθεωρήσεων",
    "### 🧾 Audit Summary": "### 🧾 Σύνοψη ελέγχου",
    "### 📊 Correlation Analysis": "### 📊 Ανάλυση συσχέτισης",
    "### 📈 Regression Analysis": "### 📈 Ανάλυση παλινδρόμησης",
    "### 📋 Data Table": "### 📋 Πίνακας δεδομένων",
    "### 📜 Methodology": "### 📜 Μεθοδολογία",
    "### 📡 Data Sources": "### 📡 Πηγές δεδομένων",
    "### ⚠️ Known Limitations": "### ⚠️ Γνωστοί περιορισμοί",

    # Explanations, empty states, and notices
    "At least two ingestion runs are required to perform historical revision audits. Sync indicators again to record a second run.": "Απαιτούνται τουλάχιστον δύο εκτελέσεις λήψης για τον έλεγχο ιστορικών αναθεωρήσεων. Συγχρονίστε ξανά τους δείκτες για να καταγραφεί δεύτερη εκτέλεση.",
    "Automatically detects unit compatibility and prevents misleading raw comparisons by re-indexing differing scales to Base Year = 100.": "Εντοπίζει ασύμβατες μονάδες και αποτρέπει παραπλανητικές συγκρίσεις κανονικοποιώντας διαφορετικές κλίμακες με έτος βάσης 100.",
    "Compare consecutive historical pipeline runs to audit retrospective revisions published by national authorities (ELSTAT) and Eurostat.": "Συγκρίνετε διαδοχικές εκτελέσεις για να ελέγξετε αναδρομικές αναθεωρήσεις από τις εθνικές αρχές (ΕΛΣΤΑΤ) και τη Eurostat.",
    "Compare selected indicators only when units and frequencies make comparison meaningful. Incompatible raw scales are automatically normalized to protect statistical integrity.": "Συγκρίνετε δείκτες μόνο όταν οι μονάδες και οι συχνότητές τους το επιτρέπουν. Οι ασύμβατες κλίμακες κανονικοποιούνται αυτόματα.",
    "Could not load run details.": "Δεν ήταν δυνατή η φόρτωση των λεπτομερειών της εκτέλεσης.",
    "Direct, unauthenticated public API wire endpoints for reproducible academic and econometric research.": "Άμεσα δημόσια τελικά σημεία API χωρίς έλεγχο ταυτότητας για αναπαραγώγιμη ακαδημαϊκή και οικονομετρική έρευνα.",
    "Generate reports documenting data provenance, configured checks, findings, and heuristic scores. These are not standards certifications.": "Δημιουργήστε αναφορές για την προέλευση δεδομένων, τους ελέγχους, τα ευρήματα και τις ενδεικτικές βαθμολογίες. Δεν αποτελούν πιστοποίηση προτύπων.",
    "Harmonized ESA 2010 / LFS / MIP series from Eurostat. Missing observations are documented transparently.": "Εναρμονισμένες σειρές ESA 2010 / ΕΕΔ / ΔΜΔ από τη Eurostat. Οι ελλείπουσες παρατηρήσεις τεκμηριώνονται με διαφάνεια.",
    "In strict adherence to our **zero-placeholder, zero-synthetic-data policy**, we do not invent or hardcode observations when an indicator lacks an open, unauthenticated public REST API. The limitations below are documented transparently:": "Σύμφωνα με την πολιτική **μηδενικών ενδεικτικών και συνθετικών δεδομένων**, δεν επινοούμε ούτε ενσωματώνουμε παρατηρήσεις όταν ένας δείκτης δεν διαθέτει ανοικτό δημόσιο REST API. Οι περιορισμοί τεκμηριώνονται παρακάτω:",
    "Inspect relationships between any two public metrics (e.g. Okun's Law: GDP vs Unemployment; Phillips Curve: Inflation vs Unemployment).": "Εξετάστε τη σχέση μεταξύ δύο δημόσιων δεικτών (π.χ. νόμος του Okun: ΑΕΠ και ανεργία· καμπύλη Phillips: πληθωρισμός και ανεργία).",
    "Insufficient overlapping observations across indicators to construct correlation matrix. Sync all indicators first.": "Δεν υπάρχουν αρκετές κοινές παρατηρήσεις για πίνακα συσχέτισης. Συγχρονίστε πρώτα όλους τους δείκτες.",
    "Less than 3 overlapping periods found between the selected indicators.": "Βρέθηκαν λιγότερες από 3 κοινές περίοδοι για τους επιλεγμένους δείκτες.",
    "Measures linear co-movement between official Greek indicators across overlapping annual observation periods (min 5 periods).": "Μετρά τη γραμμική συνδιακύμανση επίσημων ελληνικών δεικτών σε κοινές ετήσιες περιόδους (τουλάχιστον 5 περίοδοι).",
    "No indicators match your search and filter criteria.": "Κανένας δείκτης δεν αντιστοιχεί στην αναζήτηση και τα φίλτρα σας.",
    "No numeric observations in selected period range.": "Δεν υπάρχουν αριθμητικές παρατηρήσεις στο επιλεγμένο χρονικό διάστημα.",
    "No recorded audit runs for this indicator yet. Click 'Sync All Indicators' to generate audit logs.": "Δεν έχουν καταγραφεί ακόμη εκτελέσεις ελέγχου για αυτόν τον δείκτη. Επιλέξτε «Συγχρονισμός όλων των δεικτών» για δημιουργία αρχείου ελέγχου.",
    "No runs found for this series.": "Δεν βρέθηκαν εκτελέσεις για αυτή τη σειρά.",
    "No significant period shifts detected.": "Δεν εντοπίστηκαν σημαντικές μεταβολές περιόδου.",
    "No benchmark data returned from Eurostat.": "Η Eurostat δεν επέστρεψε δεδομένα σύγκρισης.",
    "No comparative values found for the latest reference year.": "Δεν βρέθηκαν συγκριτικές τιμές για το τελευταίο έτος αναφοράς.",
    "No debt data currently available in the database.": "Δεν υπάρχουν διαθέσιμα στοιχεία χρέους στη βάση δεδομένων.",
    "No indicators match your search and filter criteria.": "Κανένας δείκτης δεν αντιστοιχεί στην αναζήτηση και τα φίλτρα σας.",
    "Sync indicators first to view in-depth scorecards.": "Συγχρονίστε πρώτα τους δείκτες για να δείτε αναλυτικές βαθμολογίες.",
    "Official general government gross consolidated debt as a percentage of GDP (Eurostat table `gov_10dd_edpt1`, ESA 2010).": "Το ενοποιημένο ακαθάριστο χρέος της γενικής κυβέρνησης ως ποσοστό του ΑΕΠ (πίνακας Eurostat `gov_10dd_edpt1`, ESA 2010).",
    "The long-term sovereign bond yield reflects market perception of Greek sovereign creditworthiness. From crisis peaks (>25%), Greek yields returned to investment-grade pricing, trading on par with southern European peers.": "Η απόδοση μακροπρόθεσμων κρατικών ομολόγων αντανακλά την εκτίμηση της αγοράς για την πιστοληπτική ικανότητα της Ελλάδας. Από τα επίπεδα κρίσης (>25%), οι αποδόσεις επέστρεψαν σε επίπεδα επενδυτικής βαθμίδας, κοντά σε εκείνα χωρών της Νότιας Ευρώπης.",
    "Retrieval age describes when this app checked the source. The reference year and source flags describe the observations; a recent check does not make a value final or current-year data.": "Ο χρόνος λήψης δείχνει πότε η εφαρμογή έλεγξε την πηγή. Το έτος αναφοράς και οι σημάνσεις πηγής αφορούν τις παρατηρήσεις· ένας πρόσφατος έλεγχος δεν σημαίνει ότι η τιμή είναι οριστική ή αφορά το τρέχον έτος.",
    "✅ Zero retrospective revisions detected across historical observations between consecutive ingestion runs.": "✅ Δεν εντοπίστηκαν αναδρομικές αναθεωρήσεις μεταξύ διαδοχικών εκτελέσεων λήψης.",
    "💡 **Methodology Guidance:** Warnings indicate unusual volatility or data revisions that warrant review. A warning is a reason to inspect data, NOT definitive proof that official statistics are incorrect.": "💡 **Οδηγίες μεθοδολογίας:** Οι προειδοποιήσεις επισημαίνουν ασυνήθιστη μεταβλητότητα ή αναθεωρήσεις που χρειάζονται έλεγχο. Δεν αποδεικνύουν ότι τα επίσημα στατιστικά είναι λανθασμένα.",
    "Database contains no stored observations yet.": "Δεν υπάρχουν ακόμη αποθηκευμένες παρατηρήσεις στη βάση δεδομένων.",
    "The data is annual; choose dates in different years to compare indicators.": "Τα δεδομένα είναι ετήσια· επιλέξτε ημερομηνίες από διαφορετικά έτη για σύγκριση.",
    "The data is annual, so the selected years are compared; individual days are not available.": "Τα δεδομένα είναι ετήσια, επομένως συγκρίνονται τα επιλεγμένα έτη και όχι οι μεμονωμένες ημέρες.",
    "At least two years of stored observations are needed for a comparison. Sync the indicators, then try again.": "Χρειάζονται τουλάχιστον δύο έτη αποθηκευμένων στοιχείων. Συγχρονίστε τους δείκτες και δοκιμάστε ξανά.",
    "No clearly positive movements are available for the selected period.": "Δεν υπάρχουν σαφείς θετικές μεταβολές για την επιλεγμένη περίοδο.",
    "No clear worsening movements are available in the stored data for this period.": "Δεν υπάρχουν σαφείς αρνητικές μεταβολές στα αποθηκευμένα στοιχεία αυτής της περιόδου.",
    "These indicators moved in a direction that is generally favorable for the measure shown.": "Οι δείκτες αυτοί κινήθηκαν προς κατεύθυνση που θεωρείται γενικά θετική για το συγκεκριμένο μέγεθος.",
    "These indicators moved in a direction that can signal a worsening outcome for the measure shown.": "Οι δείκτες αυτοί κινήθηκαν προς κατεύθυνση που μπορεί να σημαίνει επιδείνωση.",
    "These indicators need extra context, were broadly stable, or do not have data for both years.": "Οι δείκτες αυτοί χρειάζονται πρόσθετο πλαίσιο, έμειναν σχεδόν σταθεροί ή δεν έχουν στοιχεία και για τα δύο έτη.",
    "This is a directional snapshot, not an overall grade for Greece. It does not identify causes, and a favorable movement in one measure does not cancel out pressure in another. Open **Sources & Methodology** to review definitions, sources, and limitations.": "Η σελίδα δείχνει τάσεις, όχι συνολική βαθμολογία ή αιτίες. Η βελτίωση σε έναν δείκτη δεν αναιρεί τις πιέσεις σε άλλον. Δείτε τις **Πηγές και μεθοδολογία** για ορισμούς και περιορισμούς.",
    "Comparing ": "Σύγκριση ",
    "Benchmark Standings": "Κατάταξη συγκριτικών στοιχείων",
    "No data available.": "Δεν υπάρχουν διαθέσιμα δεδομένα.",
    "No Data": "Χωρίς δεδομένα",
    "INFO": "ΠΛΗΡΟΦΟΡΙΑ",
    "WARN": "ΠΡΟΕΙΔΟΠΟΙΗΣΗ",
    "ERROR": "ΣΦΑΛΜΑ",

    # Tabs, exports, and format choices (format_func keeps original values)
    "Overview": "Επισκόπηση",
    "Economy": "Οικονομία",
    "People & Society": "Κοινωνία",
    "🏛️ Economy": "🏛️ Οικονομία",
    "People & Society": "Άνθρωποι και κοινωνία",
    "Tourism & Housing": "Τουρισμός και στέγαση",
    "Energy & Environment": "Ενέργεια και περιβάλλον",
    "Banking & Finance": "Τράπεζες και χρηματοοικονομικά",
    "🏛️ [Economy]": "🏛️ [Οικονομία]",
    "👥 [People & Society]": "👥 [Άνθρωποι και κοινωνία]",
    "⚡ [Energy & Environment]": "⚡ [Ενέργεια και περιβάλλον]",
    "🏖️ [Tourism]": "🏖️ [Τουρισμός]",
    "🏠 [Housing]": "🏠 [Στέγαση]",
    "🏦 [Banking & Finance]": "🏦 [Τράπεζες και χρηματοοικονομικά]",
    "Gross Domestic Product (Real, Chain-linked 2020)": "Ακαθάριστο Εγχώριο Προϊόν (πραγματικό, αλυσωτοί όγκοι 2020)",
    "Gross Domestic Product (Nominal)": "Ακαθάριστο Εγχώριο Προϊόν (ονομαστικό)",
    "Inflation Rate (HICP Annual Rate of Change)": "Πληθωρισμός (ετήσιος ρυθμός μεταβολής ΕνΔΤΚ)",
    "Unemployment Rate (Age 15–74)": "Ποσοστό ανεργίας (ηλικίες 15–74)",
    "General Government Gross Debt (% of GDP)": "Ακαθάριστο χρέος γενικής κυβέρνησης (% ΑΕΠ)",
    "Exports of Goods and Services": "Εξαγωγές αγαθών και υπηρεσιών",
    "Imports of Goods and Services": "Εισαγωγές αγαθών και υπηρεσιών",
    "Total Population (1 January)": "Συνολικός πληθυσμός (1η Ιανουαρίου)",
    "Life Expectancy at Birth": "Προσδόκιμο ζωής κατά τη γέννηση",
    "At-Risk-of-Poverty Rate (60% Median Income)": "Κίνδυνος φτώχειας (60% του διάμεσου εισοδήματος)",
    "Annual Immigration Inflow": "Ετήσια εισερχόμενη μετανάστευση",
    "Annual Emigration Outflow": "Ετήσια εξερχόμενη μετανάστευση",
    "Renewable Energy Share": "Μερίδιο ανανεώσιμης ενέργειας",
    "Greenhouse Gas Emissions": "Εκπομπές αερίων του θερμοκηπίου",
    "Final Energy Consumption": "Τελική κατανάλωση ενέργειας",
    "Tourist Arrivals (All Accommodation)": "Τουριστικές αφίξεις (όλα τα καταλύματα)",
    "Tourist Overnight Stays (Nights Spent)": "Τουριστικές διανυκτερεύσεις",
    "House Price Index (Nominal, 2015=100)": "Δείκτης τιμών κατοικιών (ονομαστικός, 2015=100)",
    "10-Year Government Benchmark Bond Yield": "Απόδοση 10ετούς κρατικού ομολόγου αναφοράς",
    "€M (vol)": "εκατ. € (όγκος)",
    "€M": "εκατ. €",
    "% GDP": "% ΑΕΠ",
    "pers.": "άτομα",
    "yrs": "έτη",
    "kt CO2e": "χιλ. τόνοι CO₂e",
    "arrivals": "αφίξεις",
    "nights": "διανυκτερεύσεις",
    "idx (2015=100)": "δείκτης (2015=100)",
    "MTOE": "Mtoe",
    "Connecting to official Eurostat APIs across all topics...": "Σύνδεση με τα επίσημα API της Eurostat σε όλους τους τομείς...",
    "Ingesting verified datasets across Economy, Society, Energy, Tourism, Housing, and Finance...": "Γίνεται λήψη ελεγμένων δεδομένων για οικονομία, κοινωνία, ενέργεια, τουρισμό, στέγαση και χρηματοοικονομικά...",
    "Fetching official Eurostat data...": "Γίνεται λήψη επίσημων δεδομένων από τη Eurostat...",
    "Connecting to Eurostat SDMX Dissemination API...": "Σύνδεση με το API διάθεσης SDMX της Eurostat...",
    "All Topics": "Όλοι οι τομείς",
    "All Sources": "Όλες οι πηγές",
    "All 19 Indicators Consolidated": "Και οι 19 δείκτες μαζί",
    "Single Selected Indicator": "Ένας επιλεγμένος δείκτης",
    "text/csv": "text/csv",
    "application/json": "application/json",
    "text/markdown": "text/markdown",
    "📥 Download CSV Dataset": "📥 Λήψη συνόλου δεδομένων CSV",
    "📥 Download JSON Dataset": "📥 Λήψη συνόλου δεδομένων JSON",
    "📥 Download Markdown Audit Report": "📥 Λήψη αναφοράς ελέγχου Markdown",
    "📥 Export Observations as CSV": "📥 Εξαγωγή παρατηρήσεων σε CSV",

    # Common chart and table vocabulary
    "Year": "Έτος",
    "Period": "Περίοδος",
    "Value": "Τιμή",
    "Country": "Χώρα",
    "Country Name": "Χώρα",
    "Series": "Σειρά",
    "Status": "Κατάσταση",
    "Severity": "Σοβαρότητα",
    "Rule": "Κανόνας",
    "Finding": "Εύρημα",
    "Message": "Μήνυμα",
    "Latest Period": "Τελευταία περίοδος",
    "Previous Period": "Προηγούμενη περίοδος",
    "Change": "Μεταβολή",
    "Change (%)": "Μεταβολή (%)",
    "Change (pp)": "Μεταβολή (π.μ.)",
    "Reference Year": "Έτος αναφοράς",
    "Reference Period": "Περίοδος αναφοράς",
    "Metric": "Μέτρηση",
    "Indicator Name": "Όνομα δείκτη",
    "Source": "Πηγή",
    "Dataset": "Σύνολο δεδομένων",
    "Unit Short": "Σύντομη μονάδα",
    "Raw Value": "Αρχική τιμή",
    "Formatted": "Μορφοποιημένη τιμή",
    "Data Quality": "Ποιότητα δεδομένων",
    "Freshness": "Επικαιρότητα",
    "Completeness": "Πληρότητα",
    "Timeliness": "Έγκαιρη ενημέρωση",
    "Reliability": "Αξιοπιστία",
    "Score": "Βαθμολογία",
    "Severity": "Σοβαρότητα",
    "No Debt data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία χρέους.",
    "No GDP data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία ΑΕΠ.",
    "No bond yield data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία απόδοσης ομολόγων.",
    "No debt data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία χρέους.",
    "No greenhouse gas data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία εκπομπών αερίων θερμοκηπίου.",
    "No house price index data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία για τον δείκτη τιμών κατοικιών.",
    "No population data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία πληθυσμού.",
    "No renewable energy data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία ανανεώσιμης ενέργειας.",
    "No tourism arrivals data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία τουριστικών αφίξεων.",
    "No unemployment data available.": "Δεν υπάρχουν διαθέσιμα στοιχεία ανεργίας.",
    "No benchmark data returned from Eurostat.": "Η Eurostat δεν επέστρεψε συγκριτικά στοιχεία.",
    "No comparative values found for the latest reference year.": "Δεν βρέθηκαν συγκριτικές τιμές για το τελευταίο έτος αναφοράς.",
    "No recorded audit runs for this indicator yet. Click 'Sync All Indicators' to generate audit logs.": "Δεν έχουν καταγραφεί εκτελέσεις ελέγχου για αυτόν τον δείκτη. Επιλέξτε «Συγχρονισμός όλων των δεικτών» για δημιουργία αρχείου ελέγχου.",
    "No runs found for this series.": "Δεν βρέθηκαν εκτελέσεις για αυτή τη σειρά.",
    "No significant period shifts detected.": "Δεν εντοπίστηκαν σημαντικές μεταβολές περιόδου.",
    "No numeric observations in selected period range.": "Δεν υπάρχουν αριθμητικές παρατηρήσεις στην επιλεγμένη περίοδο.",
    "No indicators match your search and filter criteria.": "Κανένας δείκτης δεν αντιστοιχεί στην αναζήτηση και τα φίλτρα σας.",
    "Could not load run details.": "Δεν ήταν δυνατή η φόρτωση των λεπτομερειών της εκτέλεσης.",
    "Select Active Indicator to Inspect": "Επιλέξτε ενεργό δείκτη για εξέταση",
    "Select Benchmark Indicator": "Επιλέξτε δείκτη σύγκρισης",
    "Select Dependent Variable (Y-axis)": "Επιλέξτε εξαρτημένη μεταβλητή (άξονας Y)",
    "Select Economies to Compare": "Επιλέξτε οικονομίες για σύγκριση",
    "Select Independent Variable (X-axis)": "Επιλέξτε ανεξάρτητη μεταβλητή (άξονας X)",
    "Select Indicator for API Wire Details": "Επιλέξτε δείκτη για λεπτομέρειες API",
    "Select Indicator for Detailed Methodology & Dimensions": "Επιλέξτε δείκτη για αναλυτική μεθοδολογία και διαστάσεις",
    "Select Indicator for Formal Audit": "Επιλέξτε δείκτη για επίσημο έλεγχο",
    "Select Indicator to Export": "Επιλέξτε δείκτη για εξαγωγή",
    "Select Series A": "Επιλέξτε σειρά A",
    "Select Series B": "Επιλέξτε σειρά B",
    "Select Series to Audit": "Επιλέξτε σειρά για έλεγχο",
    "Select Series to Audit Revisions": "Επιλέξτε σειρά για έλεγχο αναθεωρήσεων",
    "Baseline Run (Earlier)": "Αρχική εκτέλεση (παλαιότερη)",
    "Comparison Run (Later)": "Συγκριτική εκτέλεση (νεότερη)",
    "Export Scope": "Εύρος εξαγωγής",
    "Filter Catalog Table": "Φιλτράρισμα καταλόγου",
    "Filter Period Range": "Φιλτράρισμα περιόδου",
    "Search by name, topic, dataset code...": "Αναζήτηση ονόματος, τομέα ή κωδικού συνόλου δεδομένων...",
    "e.g. inflation, debt, tourism, renewable, bond...": "π.χ. πληθωρισμός, χρέος, τουρισμός, ανανεώσιμη ενέργεια, ομόλογα...",
    "Select Indicator for Detailed Methodology & Dimensions": "Επιλέξτε δείκτη για αναλυτική μεθοδολογία και διαστάσεις",
    "View Format": "Μορφή προβολής",
    "Headline Cards (9)": "Κύριοι δείκτες (9)",
    "All Indicators Grid (19)": "Όλοι οι δείκτες (19)",
    "Compact Table": "Συνοπτικός πίνακας",
    "Export Scope": "Εύρος εξαγωγής",
    "Single Selected Indicator": "Ένας επιλεγμένος δείκτης",
    "All 19 Indicators Consolidated": "Και οι 19 δείκτες μαζί",
    "GDP": "ΑΕΠ",
    "Gross Domestic Product": "Ακαθάριστο Εγχώριο Προϊόν",
    "Inflation": "Πληθωρισμός",
    "Unemployment": "Ανεργία",
    "Debt": "Χρέος",
    "Population": "Πληθυσμός",
    "Exports": "Εξαγωγές",
    "Imports": "Εισαγωγές",
    "Tourism": "Τουρισμός",
    "Tourist": "Τουριστικός",
    "Renewable Energy": "Ανανεώσιμη ενέργεια",
    "Energy Consumption": "Κατανάλωση ενέργειας",
    "House Price": "Τιμές κατοικιών",
    "Bond Yield": "Απόδοση ομολόγου",
    "Benchmark Yield": "Απόδοση ομολόγου αναφοράς",
    "Indicators": "Δείκτες",
    "Economies": "Οικονομίες",
    "Latest": "Τελευταία",
    "Previous": "Προηγούμενη",
    "Reference": "Αναφοράς",
    "Annual": "Ετήσιος",
    "Trend": "Τάση",
    "Quality": "Ποιότητα",
    "Comparison": "Σύγκριση",
    "Compare": "Σύγκριση",
    "Analysis": "Ανάλυση",
    "Results": "Αποτελέσματα",
    "Summary": "Σύνοψη",
    "Benchmark": "Συγκριτικό στοιχείο",
    "Standings": "Κατάταξη",
    "Audit": "Έλεγχος",
    "Records": "Εγγραφές",
    "Missing": "Ελλείποντα",
    "Available": "Διαθέσιμα",
    "Current": "Τρέχων",
    "Historical": "Ιστορικός",
    "Domains": "τομείς",
    "stored": "αποθηκευμένα",
    "Series": "Σειρά",
    "Up": "Άνοδος",
    "Down": "Πτώση",
    "Stable": "Σταθερό",
    "Greece": "Ελλάδα",
    "Germany": "Γερμανία",
    "Italy": "Ιταλία",
    "Spain": "Ισπανία",
    "Portugal": "Πορτογαλία",
    "Cyprus": "Κύπρος",
    "European Union": "Ευρωπαϊκή Ένωση",
}


def translate_text(value: Any) -> Any:
    """Translate visible English copy to Greek while leaving unknown text intact."""
    if not _GREEK or not isinstance(value, str):
        return value
    exact = TRANSLATIONS.get(value)
    if exact is not None:
        return exact
    translated = value
    import re
    for source in sorted(TRANSLATIONS, key=len, reverse=True):
        if len(source) > 16 and source in translated:
            translated = translated.replace(source, TRANSLATIONS[source])
        elif source.isascii() and source and source[0].isalnum():
            translated = re.sub(rf"\b{re.escape(source)}\b", TRANSLATIONS[source], translated)
        elif source and source in translated:
            translated = translated.replace(source, TRANSLATIONS[source])
    return translated


def configure_language(greek: bool) -> None:
    """Set the active locale and localize Streamlit's shared display methods."""
    global _GREEK, _INSTALLED
    _GREEK = greek
    if _INSTALLED:
        return

    from streamlit.delta_generator import DeltaGenerator

    text_positions = {
        "markdown": (0,), "caption": (0,), "info": (0,), "warning": (0,),
        "error": (0,), "success": (0,), "title": (0,), "header": (0,),
        "subheader": (0,), "text": (0,), "button": (0,), "metric": (0, 1, 2),
        "radio": (0,), "selectbox": (0,), "multiselect": (0,), "checkbox": (0,),
        "toggle": (0,), "text_input": (0,), "number_input": (0,), "date_input": (0,),
        "slider": (0,), "select_slider": (0,), "file_uploader": (0,),
        "download_button": (0,), "expander": (0,), "form_submit_button": (0,),
        "spinner": (0,), "status": (0,), "toast": (0,), "progress": (),
        "page_link": (1,), "tabs": (), "dataframe": (), "plotly_chart": (),
    }
    for method_name, positions in text_positions.items():
        if not hasattr(DeltaGenerator, method_name):
            continue
        original = getattr(DeltaGenerator, method_name)

        @wraps(original)
        def localized(self, *args, __original=original, __positions=positions, __name=method_name, **kwargs):
            args = list(args)
            for position in __positions:
                if position < len(args):
                    args[position] = translate_text(args[position])
            for key in ("label", "help", "placeholder", "text"):
                if key in kwargs:
                    kwargs[key] = translate_text(kwargs[key])

            # Display translated choices while preserving the original values
            # returned to application logic.
            if _GREEK and __name in {"radio", "selectbox", "multiselect", "select_slider"}:
                old_format = kwargs.get("format_func", lambda option: option)
                kwargs["format_func"] = lambda option, formatter=old_format: translate_text(str(formatter(option)))
            if _GREEK and __name == "tabs" and args and isinstance(args[0], (list, tuple)):
                args[0] = [translate_text(label) for label in args[0]]

            if _GREEK and __name == "dataframe":
                try:
                    import pandas as pd
                    data = args[0] if args else kwargs.get("data")
                    if isinstance(data, pd.DataFrame):
                        display_df = data.copy()
                        display_df.columns = [translate_text(str(column)) for column in display_df.columns]
                        for column in display_df.select_dtypes(include=["object", "string"]).columns:
                            display_df[column] = display_df[column].map(translate_text)
                        if args:
                            args[0] = display_df
                        else:
                            kwargs["data"] = display_df
                except (ImportError, TypeError, AttributeError):
                    pass

            if _GREEK and __name == "plotly_chart":
                figure_arg = args[0] if args else kwargs.get("figure_or_data")
                if not hasattr(figure_arg, "update_layout"):
                    return __original(self, *args, **kwargs)
                figure = deepcopy(figure_arg)
                for part in ("title",):
                    text = getattr(figure.layout, part, None)
                    if text is not None and getattr(text, "text", None):
                        figure.update_layout(**{part: {"text": translate_text(text.text)}})
                for axis in ("xaxis", "yaxis", "yaxis2"):
                    axis_obj = getattr(figure.layout, axis, None)
                    title = getattr(axis_obj, "title", None)
                    if title is not None and getattr(title, "text", None):
                        figure.update_layout(**{axis: {"title": {"text": translate_text(title.text)}}})
                for trace in figure.data:
                    if isinstance(getattr(trace, "name", None), str):
                        trace.name = translate_text(trace.name)
                if args:
                    args[0] = figure
                else:
                    kwargs["figure_or_data"] = figure
            return __original(self, *args, **kwargs)

        setattr(DeltaGenerator, method_name, localized)

    # A few display methods accept arbitrary text/data rather than a label.
    original_write = DeltaGenerator.write

    @wraps(original_write)
    def localized_write(self, *args, **kwargs):
        args = tuple(translate_text(item) if isinstance(item, str) else item for item in args)
        return original_write(self, *args, **kwargs)

    DeltaGenerator.write = localized_write

    _INSTALLED = True

"""Build a source-only Overleaf archive and verify both clean builds."""
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PAPER = Path(__file__).resolve().parent
ARCHIVE = PAPER / "CapFill-Overleaf.zip"
TARGETS = ("main", "extended")


def run(*args, cwd=None):
    return subprocess.check_output(args, cwd=cwd, stderr=subprocess.STDOUT)


def package_inputs():
    files = {
        "references.bib", "IEEEtran.bst", "IEEEtran.cls", "build.sh",
        "main.tex", "extended.tex",
    }
    for target in TARGETS:
        recorder = (PAPER / f"{target}.fls").read_text()
        for name in re.findall(r"^INPUT (.+)$", recorder, flags=re.MULTILINE):
            source = (PAPER / name).resolve()
            if source.is_relative_to(PAPER) and source.suffix in {".tex", ".pdf", ".png"}:
                files.add(source.relative_to(PAPER).as_posix())
    return sorted(files)


def check_pdf(directory, target):
    pdf = directory / f"{target}.pdf"
    log = (directory / f"{target}.log").read_text(errors="replace")
    bad = re.search(r"Overfull|multiply defined|undefined (?:references|citations)|LaTeX Warning: (?:Reference|Citation)", log)
    if bad:
        raise ValueError(f"{target} log: {bad.group()}")
    fonts = run("pdffonts", str(pdf)).decode().splitlines()[2:]
    assert fonts and all("Type 3" not in font and font.split()[-5] == "yes" for font in fonts)
    raw_boxes = run("pdftotext", "-bbox", str(pdf), "-")
    # Poppler may transcribe a math glyph as a control byte invalid in XML.
    document = ET.fromstring(re.sub(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]", b"", raw_boxes))
    pages = document.findall(".//{*}page")
    for page in pages:
        words = page.findall("{*}word")
        assert words
        for word in words:
            assert 0 <= float(word.attrib["xMin"]) < float(word.attrib["xMax"]) <= float(page.attrib["width"])
            assert 0 <= float(word.attrib["yMin"]) < float(word.attrib["yMax"]) <= float(page.attrib["height"])
    if target == "main":
        assert len(pages) == 7
        text = run("pdftotext", "-f", "7", "-l", "7", str(pdf), "-").decode().lower()
        assert "references" in text[:25].replace(" ", "")
    return len(pages)


def compare_build(target, directory):
    with ZipFile(ARCHIVE) as archive:
        archive.extractall(directory)
    try:
        run("bash", "build.sh", target, cwd=directory)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(exc.output.decode(errors="replace")[-6000:]) from exc
    num_pages = check_pdf(directory, target)
    reference = PAPER / f"{target}.pdf"
    rebuilt = directory / reference.name
    assert run("pdftotext", "-layout", str(reference), "-") == run("pdftotext", "-layout", str(rebuilt), "-")
    for version, pdf in [("saved", reference), ("rebuilt", rebuilt)]:
        run("pdftoppm", "-r", "100", str(pdf), str(directory / version))
    for image in directory.glob("saved-*.ppm"):
        other = directory / image.name.replace("saved-", "rebuilt-")
        assert image.read_bytes() == other.read_bytes(), image.name
    assert len(list(directory.glob("saved-*.ppm"))) == num_pages
    print(f"{target}: {num_pages} pages, embedded fonts, identical text and page rasters")


if __name__ == "__main__":
    inputs = package_inputs()
    with ZipFile(ARCHIVE, "w") as archive:
        for name in inputs:
            info = ZipInfo(name, date_time=(2026, 11, 18, 0, 0, 0))
            archive.writestr(info, (PAPER / name).read_bytes(), compress_type=ZIP_DEFLATED)
    print(f"{ARCHIVE.name}: {len(inputs)} build inputs")
    for target in TARGETS:
        with tempfile.TemporaryDirectory(prefix=f"capfill-academic-{target}-") as tmp:
            compare_build(target, Path(tmp))

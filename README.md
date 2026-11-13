# eval-mutation-validity

Does the mutation score of an LLM eval suite predict whether that suite
catches real regressions? This project reproduces real regressions from
open-source LLM applications as pairs of commits, runs each application's own
eval suite repeatedly at both commits and under sampled mutants, and measures
how well mutation score predicts detection at fixed suite size.

## Contents

- `proposal/`: the project plan in LaTeX, with the rendered PDF in
  `proposal/build/main.pdf`.
- `mockup.html`: a static mock-up of the results console. Open it in a browser.
- `corpus/`: regression records.

## Building the plan

From `proposal/`, with a TeX distribution that provides LuaLaTeX and latexmk:

```sh
latexmk
```

## Licence

Code is under the MIT licence (`LICENSE`). Corpus records and results are
under CC BY 4.0 (`corpus/LICENSE`). Code from target applications keeps its
own licence.

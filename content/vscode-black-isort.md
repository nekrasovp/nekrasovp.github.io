Title: Use Black and organize imports on save in VSCode
Author: Nekrasov Pavel
Date: 2022-05-10 12:00
Category: Blog
Tags: python, vscode, black
Slug: python-black-isort
Summary: How to use Black to format python code, and organise imports on save.

How to use Black to format Python code, and organise imports on save in VSCode.

Here’s the relevant bit of VSCode’s **settings.json**:

```json
{
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

It turns out that VS Code uses the **isort** library to sort imports, and **isort** has a **Black** compatability profile.

If you use **Poetry**, add these lines to the **pyproject.toml** file at the root of the project:

```cfg
[tool.isort]
profile = "black"
```

Alternatively, create a file called **.isort.cfg** at the root of the project, with this content:

```cfg
[settings]
profile=black
```

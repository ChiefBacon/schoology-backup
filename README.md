# Schoology Backup
A simple tool to help back up course data from Schoology!

## Usage
To install the needed dependencies, just run

```bash
uv sync
```

Set up your config file based on the `example-config.toml`

> [!NOTE]  
> You can retrieve API keys by going to https://app.schoology.com/api
> If your school uses a different URL, you should be able to use that with the /api page as well

To run the program, just run

```bash
uv run main.py
```

> [!IMPORTANT]  
> Some schools may block some or all of the API access that this program needs.

## Questions/Comments
Open an issue and I'll try my best to help out!

## Contributions
All contributions are welcome! Just make a pull request and I will have a look at it.

## License
This project is licensed under the Mozilla Public License 2.0
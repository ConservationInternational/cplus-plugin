# SPDX-FileCopyrightText: Tim Sutton
# SPDX-License-Identifier: MIT
{
  description = "NixOS developer environment for QGIS plugins.";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      pkgsFor = system: import nixpkgs {
        inherit system;
        config.allowUnfree = true;
      };
    in
    {
      packages = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          postgresWithPostGIS = pkgs.postgresql.withPackages (ps: [ ps.postgis ]);
        in
        {
          default = postgresWithPostGIS;
          postgres = postgresWithPostGIS;
        });


      devShells = forAllSystems (system:
        let
          pkgs = pkgsFor system;
          postgresWithPostGIS = pkgs.postgresql.withPackages (ps: [ ps.postgis ]);
        in
        {
          default = pkgs.mkShell {
        packages = [

          pkgs.actionlint # for checking gh actions
          pkgs.bandit
          pkgs.bearer
          pkgs.chafa
          pkgs.nixfmt-rfc-style
          pkgs.codeql
          pkgs.ffmpeg
          pkgs.gdb
          pkgs.git
          pkgs.minio-client # for grabbing ookla data
          pkgs.glogg
          pkgs.glow # terminal markdown viewer
          pkgs.gource # Software version control visualization
          pkgs.gum # UX for TUIs
          pkgs.isort
          pkgs.jq
          pkgs.luaPackages.luacheck
          pkgs.markdownlint-cli
          pkgs.nixfmt-rfc-style
          pkgs.pre-commit
          pkgs.nixfmt-rfc-style
          pkgs.pyprof2calltree # needed to covert cprofile call trees into a format kcachegrind can read
          pkgs.python313
          # Python development essentials
          pkgs.pyright
          pkgs.rpl
          pkgs.shellcheck
          pkgs.shfmt
          pkgs.stylua
          pkgs.yamlfmt
          pkgs.yamllint
          postgresWithPostGIS
          pkgs.nodePackages.cspell
          (pkgs.python313.withPackages (ps: [
            # Add these for SQL linting/formatting:
            ps.black
            ps.click # needed by black
            ps.debugpy
            ps.docformatter
            ps.flake8
            ps.gdal
            ps.httpx
            ps.jsonschema
            ps.mypy
            ps.numpy
            ps.odfpy
            ps.pandas
            ps.paver
            ps.pip
            ps.psutil
            ps.pytest
            ps.rich
            ps.setuptools
            ps.snakeviz # For visualising cprofiler outputs
            ps.sqlfmt
            ps.toml
            ps.typer
            ps.wheel
            # For autocompletion in vscode

            # This executes some shell code to initialize a venv in $venvDir before
            # dropping into the shell
            ps.venvShellHook
            ps.virtualenv
          ]))

        ];
        shellHook = ''
            unset SOURCE_DATE_EPOCH

            # Create a virtual environment in .venv if it doesn't exist
             if [ ! -d ".venv" ]; then
              python -m venv .venv
            fi

            # Activate the virtual environment
            source .venv/bin/activate

            # Upgrade pip and install packages from requirements.txt if it exists
            pip install --upgrade pip > /dev/null
            if [ -f requirements.txt ]; then
              echo "Installing Python requirements from requirements.txt..."
              pip install -r requirements.txt > .pip-install.log 2>&1
              if [ $? -ne 0 ]; then
                echo "❌ Pip install failed. See .pip-install.log for details."
              fi
            else
              echo "No requirements.txt found, skipping pip install."
            fi
            if [ -f requirements-dev.txt ]; then
              echo "Installing Python requirements from requirements-dev.txt..."
              pip install -r requirements-dev.txt > .pip-install.log 2>&1
              if [ $? -ne 0 ]; then
                echo "❌ Pip install failed. See .pip-install.log for details."
              fi
            else
              echo "No requirements-dev.txt found, skipping pip install."
            fi

            echo "Setting up and running pre-commit hooks..."
            echo "-------------------------------------"
            pre-commit clean > /dev/null
            pre-commit install --install-hooks > /dev/null
            pre-commit run --all-files || true

            # Colors and styling
            CYAN='\033[38;2;83;161;203m'
            GREEN='\033[92m'
            RED='\033[91m'
            RESET='\033[0m'
            ORANGE='\033[38;2;237;177;72m'
            GRAY='\033[90m'
            # Clear screen and show welcome banner
            clear
            echo -e "$RESET$ORANGE"
            echo -e "        🌈 Your Dev Environment is prepared."
            echo -e ""
            echo -e "Quick Commands:$RESET"
            echo -e "   $GRAY▶$RESET  $CYAN nix flake show$RESET    - Show available configurations"
            echo -e "   $GRAY▶$RESET  $CYAN nix flake check$RESET   - Run all checks"
            echo -e "$RESET$ORANGE \n__________________________________________________________________\n"
            echo ""
        '';
          };
        });
    };
}


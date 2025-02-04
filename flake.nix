{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    inputs@{
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
      in
      {
        packages.default = poetry2nix.mkPoetryApplication {
          python = pkgs.python312;
          projectDir = self;

          overrides = poetry2nix.overrides.withDefaults (
            self: super: {
              # There HAS to be a better way to handle this, rather than repeating a bunch or making a helper function
              textual-autocomplete = super.textual-autocomplete.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [
                  self.hatch-vcs
                ];
              });

              pyserde = super.pyserde.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [
                  self.hatch-vcs
                ];
              });

              beartype = super.beartype.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [
                  self.hatch-vcs
                ];
              });

              py-gitea = super.py-gitea.overridePythonAttrs (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [
                  self.hatch-vcs
                  self.setuptools
                ];
              });
            }
          );
        };

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.default ];
          packages = [
            pkgs.poetry
            pkgs.ruff
            pkgs.python312Packages.python-lsp-server
            pkgs.vscode-langservers-extracted
            pkgs.python312Packages.mypy
            pkgs.python312Packages.pylsp-mypy
            pkgs.python312Packages.setuptools
            pkgs.python312Packages.textual-dev
            pkgs.python312Packages.gitpython
            pkgs.python312Packages.tree-sitter
            pkgs.python312Packages.tree-sitter-languages
            pkgs.tree-sitter
          ];
        };
      }
    );
}

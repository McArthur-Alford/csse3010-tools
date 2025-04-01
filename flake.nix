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
        poetryPkg = poetry2nix.mkPoetryApplication {
          python = pkgs.python312;
          projectDir = self;
          preferWheels = true;

          overrides =
            let
              pypkgs-build-requirements = {
                textual-autocomplete = [
                  "setuptools"
                  "hatch-vcs"
                ];
                pyserde = [
                  "hatch-vcs"
                ];
                textual = [ "hatch-vcs" ];
                beartype = [ "hatch-vcs" ];
                py-gitea = [
                  "hatch-vcs"
                  "setuptools"
                ];
                pyte = [ ];
              };
            in
            poetry2nix.defaultPoetryOverrides.extend (
              final: prev:
              builtins.mapAttrs (
                package: build-requirements:
                (builtins.getAttr package prev).overridePythonAttrs (old: {
                  buildInputs =
                    (old.buildInputs or [ ])
                    ++ (builtins.map (
                      pkg: if builtins.isString pkg then builtins.getAttr pkg prev else pkg
                    ) build-requirements);
                })
              ) pypkgs-build-requirements
            );
        };
      in
      {
        apps.default = {
          type = "app";
          program = "${poetryPkg}/bin/main";
        };

        packages.default = poetryPkg;

        devShells.default = pkgs.mkShell {
          inputsFrom = [ self.packages.${system}.default ];
          packages = [
            pkgs.poetry
            pkgs.ruff
            pkgs.python312Packages.python-lsp-server
            pkgs.vscode-langservers-extracted
            pkgs.python312Packages.textual-dev
            # pkgs.gcc-arm-embedded
          ];
        };
      }
    );
}

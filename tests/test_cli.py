"""Tests unitaires pour la CLI (cli.py)."""

import unittest

from livraison_express_lite.cli import build_parser, main


class TestCli(unittest.TestCase):
    def test_build_parser_commands(self):
        parser = build_parser()
        args_serve = parser.parse_args(["serve", "--port", "8000"])
        self.assertEqual(args_serve.command, "serve")
        self.assertEqual(args_serve.port, 8000)

        args_train = parser.parse_args(["train"])
        self.assertEqual(args_train.command, "train")

        args_predict = parser.parse_args(["predict", "--file", "order.json"])
        self.assertEqual(args_predict.command, "predict")
        self.assertEqual(args_predict.file, "order.json")

    def test_predict_command(self):
        exit_code = main(["predict", "--file", "order.json"])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()


{-# LANGUAGE OverloadedStrings #-}
{-# LANGUAGE ScopedTypeVariables #-}

{-|
    Module:     ABCTree
    Copyright:  (c) T. N. Hayashi, 2020
    License:    Undetermined
    Provide utilities for ABC Trees.
-}
module ABCTree (
    -- * Data Types
    ABCTree
    -- * Printers
    -- ** Printer options
    , BranchPrintOption(..)
    -- ** Printer functions
    , printABCTree
    -- * Data (Reexported from Data.Tree)
    , module Data.Tree
    ) where

import Data.Tree
import qualified Data.Text.Prettyprint.Doc as PDoc

import ABCCat
import CatPlus

type ABCTree = Tree (CatPlus ABCCat)

data BranchPrintOption = Indented | OneLine deriving (Eq, Show)

printABCTree :: 
    BranchPrintOption 
    -> CatPlusPrintOption 
    -> ABCTree 
    -> PDoc.Doc ann
printABCTree Indented _ (Node label [])
    = PDoc.group $ PDoc.pretty label
printABCTree Indented nOp (Node label children) 
    = PDoc.parens $ 
        (printCatPlus nOp label)
        PDoc.<+> (
            PDoc.align 
            $ PDoc.vsep 
            $ printABCTree Indented nOp <$> children
            )
printABCTree OneLine nOp tr
    = PDoc.group $ printABCTree Indented nOp tr

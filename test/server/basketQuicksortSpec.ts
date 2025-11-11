/*
 * Copyright (c) 2014-2025 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import { quicksort } from '../../routes/basket'

import chai from 'chai'
const expect = chai.expect

describe('quicksort', () => {
  describe('basic functionality', () => {
    it('returns empty array for empty input', () => {
      const result = quicksort<number>([])
      expect(result).to.deep.equal([])
    })

    it('returns single element array unchanged', () => {
      const result = quicksort([42])
      expect(result).to.deep.equal([42])
    })

    it('sorts two elements correctly', () => {
      const result = quicksort([2, 1])
      expect(result).to.deep.equal([1, 2])
    })

    it('sorts an unsorted array of numbers', () => {
      const result = quicksort([3, 1, 4, 1, 5, 9, 2, 6])
      expect(result).to.deep.equal([1, 1, 2, 3, 4, 5, 6, 9])
    })

    it('sorts negative numbers correctly', () => {
      const result = quicksort([3, -1, 4, -5, 2, 0])
      expect(result).to.deep.equal([-5, -1, 0, 2, 3, 4])
    })

    it('sorts floating point numbers', () => {
      const result = quicksort([3.5, 1.2, 4.8, 2.1])
      expect(result).to.deep.equal([1.2, 2.1, 3.5, 4.8])
    })
  })

  describe('edge cases', () => {
    it('handles already sorted array', () => {
      const result = quicksort([1, 2, 3, 4, 5])
      expect(result).to.deep.equal([1, 2, 3, 4, 5])
    })

    it('handles reverse sorted array', () => {
      const result = quicksort([5, 4, 3, 2, 1])
      expect(result).to.deep.equal([1, 2, 3, 4, 5])
    })

    it('handles array with all identical elements', () => {
      const result = quicksort([7, 7, 7, 7, 7])
      expect(result).to.deep.equal([7, 7, 7, 7, 7])
    })

    it('handles array with many duplicates', () => {
      const result = quicksort([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5])
      expect(result).to.deep.equal([1, 1, 2, 3, 3, 4, 5, 5, 5, 6, 9])
    })

    it('handles large array', () => {
      const input = Array.from({ length: 1000 }, (_, i) => 1000 - i)
      const result = quicksort(input)
      const expected = Array.from({ length: 1000 }, (_, i) => i + 1)
      expect(result).to.deep.equal(expected)
    })
  })

  describe('string sorting', () => {
    it('sorts strings alphabetically', () => {
      const result = quicksort(['banana', 'apple', 'cherry', 'date'])
      expect(result).to.deep.equal(['apple', 'banana', 'cherry', 'date'])
    })

    it('handles empty strings', () => {
      const result = quicksort(['hello', '', 'world', ''])
      expect(result).to.deep.equal(['', '', 'hello', 'world'])
    })

    it('sorts case-sensitive strings', () => {
      const result = quicksort(['Zebra', 'apple', 'Banana', 'cherry'])
      expect(result).to.deep.equal(['Banana', 'Zebra', 'apple', 'cherry'])
    })
  })

  describe('custom comparison function', () => {
    it('sorts numbers in descending order with custom comparator', () => {
      const result = quicksort([3, 1, 4, 1, 5, 9, 2], (a, b) => b - a)
      expect(result).to.deep.equal([9, 5, 4, 3, 2, 1, 1])
    })

    it('sorts strings case-insensitively with custom comparator', () => {
      const result = quicksort(
        ['Zebra', 'apple', 'Banana', 'cherry'],
        (a, b) => a.toLowerCase().localeCompare(b.toLowerCase())
      )
      expect(result).to.deep.equal(['apple', 'Banana', 'cherry', 'Zebra'])
    })

    it('sorts objects by property', () => {
      interface Product {
        name: string
        price: number
      }
      const products: Product[] = [
        { name: 'Apple', price: 1.5 },
        { name: 'Banana', price: 0.5 },
        { name: 'Cherry', price: 3.0 },
        { name: 'Date', price: 2.0 }
      ]
      const result = quicksort(products, (a, b) => a.price - b.price)
      expect(result).to.deep.equal([
        { name: 'Banana', price: 0.5 },
        { name: 'Apple', price: 1.5 },
        { name: 'Date', price: 2.0 },
        { name: 'Cherry', price: 3.0 }
      ])
    })

    it('sorts objects by name alphabetically', () => {
      interface Item {
        name: string
        id: number
      }
      const items: Item[] = [
        { name: 'Zebra', id: 1 },
        { name: 'Apple', id: 2 },
        { name: 'Mango', id: 3 }
      ]
      const result = quicksort(items, (a, b) => a.name.localeCompare(b.name))
      expect(result).to.deep.equal([
        { name: 'Apple', id: 2 },
        { name: 'Mango', id: 3 },
        { name: 'Zebra', id: 1 }
      ])
    })
  })

  describe('immutability', () => {
    it('does not modify the original array', () => {
      const original = [3, 1, 4, 1, 5, 9, 2, 6]
      const originalCopy = [...original]
      quicksort(original)
      expect(original).to.deep.equal(originalCopy)
    })
  })

  describe('stability with duplicates', () => {
    it('maintains relative order of equal elements', () => {
      interface Item {
        value: number
        index: number
      }
      const items: Item[] = [
        { value: 3, index: 0 },
        { value: 1, index: 1 },
        { value: 3, index: 2 },
        { value: 1, index: 3 },
        { value: 2, index: 4 }
      ]
      const result = quicksort(items, (a, b) => a.value - b.value)
      expect(result[0].value).to.equal(1)
      expect(result[1].value).to.equal(1)
      expect(result[2].value).to.equal(2)
      expect(result[3].value).to.equal(3)
      expect(result[4].value).to.equal(3)
    })
  })
})


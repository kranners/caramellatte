---
id: Don't Use Lodash
aliases: []
tags:
  - javascript
  - opinion
---

[home](../../)

# Don't Use [Lodash](https://lodash.com/) (anymore)

> **"Why should I write a function if there's just a library for it?"**
>
> _JavaScript clown 🤡_

**TLDR**
- Lodash functions are unnecessary. Use built-in functions.
- Lodash served a solid purpose before native replacements.
- Dependencies carry risk and maintenance overhead. Avoid them.

#### Dependencies generate work

Dependencies are debt, which constantly collects. Anyone who has spent any time in software development will be familiar with a ticket that reads something like this:

```
Upgrade from React 16 to React 18
(estimated time: 2 weeks)
```
Or
```
Upgrade some-css-in-js-library to X.X
(estimated time: 1 week)
```

Dependencies force you to play their game, and will generate work for you forever. That is, until they stop being maintained.

In a stable language, libraries can complete and guarantee their
future compatibility.

The JavaScript ecosystem moves fast enough that packages need to keep up, or
risk falling out of compatibility with everything else.

There are also security risks for any dependency, installing the next *[leftpad incident](https://qz.com/646467/how-one-programmer-broke-the-internet-by-deleting-a-tiny-piece-of-code)* or *[node-ipc incident](https://www.lunasec.io/docs/blog/node-ipc-protestware/)*.

Malicious npm packages are [not even considered uncommon](https://thehackernews.com/2023/08/malicious-npm-packages-found.html). **Edit:** [Happened again](https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem).

## The point of Lodash

Pre-[ES2009 (ES5)](https://www.w3schools.com/js/js_es5.asp) and [ES2015 (ES6)](https://www.w3schools.com/js/js_es6.asp), Lodash made a lot of sense.

Generally, it performs two (very common) functions - iterating and type checking.
### Iterating over stuff

Imagine needing to filter some incoming data, and `.filter()` doesn't exist.

You could write:
```javascript
var fruits = [
	{ name: 'banana', price: 1.5 },
	{ name: 'apple', price: 1.0 },
	{ name: 'blueberry', price: 3 },
	{ name: 'mango', price: 2.1 },
];

var expensiveFruit = [];

// for..in and for..of do not exist yet either, those are in ES2015.
for (var i = 0; i < fruits.length; i++) {
	if (fruits[i]['price'] > 2) {
		expensiveFruit.push(fruits[i]);
	}
}

// expensiveFruit = blueberry, mango
```

But with Lodash:
```javascript
var _ = require('lodash');

// expensiveFruit = blueberry, mango
var expensiveFruit = _.filter(fruits, function(f) {
	return f['price'] > 2;
});
```
This is declarative rather than imperative and, is personally more readable.

Or when iterating:
```javascript
// Vanilla pre-ES2009
var fruitNames = [];
for (var i = 0; i < fruits.length; i++) {
	fruitNames.push(fruits[i]['name']);
}

// Lodash
var fruitNames = _.map(fruits, 'name');
```

### Runtime type checking

Let's say at runtime, you want to be certain that you have been passed an array, and that array has some values in it. [Reliably doing this just did not exist for a long while](http://blog.niftysnippets.org/2010/09/say-what.html):

```javascript
function isArray(obj) {
	// This catches false, null, undefined, NaN, 0 and ""
	if (!obj) {
		return false;
	}

	// This catches string, number, true
	if (typeof obj !== 'object') {
		return false;
	}

	if (obj['length'] && obj['length'] > 0) {
		return true;
	}
}
```

There are other ways of doing this, none of them good:
```javascript
function isArray(obj) {
	// You need a JavaScript degree to tell me what this means.
	return Object.prototype.toString.call(obj) === '[object Array]';
}
```

In Lodash:
```javascript
// Is it an array?
_.isArray(arr)) {

// Is the array empty?
_.isEmpty(arr)
```

That is _so much nicer_.

## Post ES2015

ES2009 and ES2015 added more type checking and iterating methods, as well as
arrow syntax.

Modern JS reads like this:
```javascript
const doStuffOrExit = (arr) => {
	// All the type checking we need.
	if (!Array.isArray(arr)) return false;

	return arr.map((e) => { ... });
}
```

Need the fruit names like before?
```javascript
const fruitNames = fruits.map((f) => f['name']);
```

Need to filter it to the expensive ones?
```javascript
const expensiveFruits = fruits.filter((f) => f['price'] > 2);
```

Want to sum their prices?
```javascript
const priceSum = fruits.reduce((acc, f) => acc + f['price'], 0);
```

## Never say *never use something*

There are non-trivial Lodash functions like `cloneDeep()` or `memoize()`.

In vanilla JS, deeply cloning an Object can be a pain:
```javascript
// Some complicated, nested object
const something = { 
	a: [ "hello", "goodbye" ], // typeof object
	b: (...args) => null, // typeof function
	c: { fruit: "banana" }, // typeof object
	d: 5, // typeof number
};

const shallow = { ...something };
```

the spread operator `...` assigns the keys of `shallow` to `something`.

The objects that you copy using this method are the same references as before:
```javascript
const shallow = { ...something };

// shallow.c and something.c now refer to the same object in memory.
shallow['c']['fruit'] = "apple";

// It's the same with the array.
something['a'][1] = "ciao";
```

You could serialize and unserialize to get a deeper clone, but then your data needs to be serializable all the time:
```javascript
const serialized = JSON.parse(JSON.stringify(something));

// Uncaught TypeError: undefined is not a function
// :(
serialized['b']();
```

Or Lodash `cloneDeep`:
```javascript
import cloneDeep from 'lodash/fp/cloneDeep';
const clone = cloneDeep(something);

// false - Objects are cloned
clone['a'] === something['a'];

// false - Primitives are also cloned
clone['d'] === something['d']

// true - Functions just copy over the reference
clone['c'] === something['c']
```

It's a niche use case but it works - install the standalone package

## Speak the same language

Lodash has other functions for manipulating data which can be useful like `sortBy()` and `uniqBy()`.

In JS, sorting by default is done by converting the values into strings, then sorting alphabetically.
```javascript
const unsorted = [ 1, 2, 10, 15, 25, 3, 6, 8 ];

// [ 1, 10, 15, 2, 25, 3, 6, 8 ]
const sorted = [...unsorted].sort();
```

Lodash has much more reasonable defaults for sorting:
```javascript
// [ 1, 2, 3, 6, 8, 10, 15, 25 ]
const actuallySorted = _.sortBy(unsorted);
```

It can be useful for complicated mutations, but you shouldn't need them if you
have a sensible data structure.

As much as possible, try to speak JavaScript instead of Lodash, it works
everywhere.


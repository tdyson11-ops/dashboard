/* Shared meal data — single source of truth for both apps.
   Loaded by meals.html (Meal planner) and shopping.html (Shopping list).
   Edit recipes, targets and the Morrisons aisle map here. */

  // ─────────────────────────────────────────────
  // Trainer targets — lean bulk 72 → 77 kg
  // High protein, calorie surplus. Tune here.
  // ─────────────────────────────────────────────
  var TARGET = { kcal: 3200, p: 190 };

  // ─────────────────────────────────────────────
  // Morrisons aisle map (item -> section)
  // ─────────────────────────────────────────────
  var CAT_ORDER = [
    'Fruit & Veg', 'Meat & Poultry', 'Fish',
    'Dairy, Eggs & Chilled', 'Bakery', 'Food Cupboard'
  ];

  var CAT = {
    'Banana': 'Fruit & Veg', 'Spinach': 'Fruit & Veg', 'Blueberries': 'Fruit & Veg',
    'Mixed peppers': 'Fruit & Veg', 'Onion': 'Fruit & Veg', 'Red onion': 'Fruit & Veg',
    'Sweet potato': 'Fruit & Veg', 'Tenderstem broccoli': 'Fruit & Veg',
    'New potatoes': 'Fruit & Veg', 'Baby potatoes': 'Fruit & Veg', 'Potatoes': 'Fruit & Veg',
    'Carrots': 'Fruit & Veg',
    'Chicken breast': 'Meat & Poultry', 'Beef mince 5%': 'Meat & Poultry',
    'Rump steak': 'Meat & Poultry', 'Chicken thighs': 'Meat & Poultry',
    'Turkey mince': 'Meat & Poultry', 'Wafer thin ham': 'Meat & Poultry',
    'Salmon fillet': 'Fish', 'Tinned tuna': 'Food Cupboard',
    'Semi-skimmed milk': 'Dairy, Eggs & Chilled', 'Eggs': 'Dairy, Eggs & Chilled',
    'Mature cheddar': 'Dairy, Eggs & Chilled', 'Butter': 'Dairy, Eggs & Chilled',
    'Greek yogurt': 'Dairy, Eggs & Chilled', 'Reduced-fat creme fraiche': 'Dairy, Eggs & Chilled',
    'Parmesan': 'Dairy, Eggs & Chilled', 'Light mozzarella': 'Dairy, Eggs & Chilled',
    'Cottage cheese': 'Dairy, Eggs & Chilled',
    'Bagels': 'Bakery', 'Wholemeal bread': 'Bakery',
    'Porridge oats': 'Food Cupboard', 'Whey protein': 'Food Cupboard',
    'Peanut butter': 'Food Cupboard', 'Honey': 'Food Cupboard', 'Granola': 'Food Cupboard',
    'Mixed nuts': 'Food Cupboard', 'Basmati rice': 'Food Cupboard', 'Olive oil': 'Food Cupboard',
    'Sweetcorn': 'Food Cupboard', 'Red kidney beans': 'Food Cupboard',
    'Chopped tomatoes': 'Food Cupboard', 'Pasta': 'Food Cupboard', 'Spaghetti': 'Food Cupboard',
    'Passata': 'Food Cupboard', 'Beef gravy': 'Food Cupboard', 'Rice cakes': 'Food Cupboard',
    'Raisins': 'Food Cupboard', 'Almonds': 'Food Cupboard'
  };

  // ─────────────────────────────────────────────
  // Recipe library — high protein, high calorie.
  // ing: [item, qty, unit]  (unit: g | ml | x)  — quantities are PER SERVING.
  // ─────────────────────────────────────────────
  var RECIPES = {
    // ── Breakfast ──
    b_oats: {
      name: 'Protein overnight oats', type: 'breakfast', kcal: 640, p: 42, c: 74, f: 20,
      note: 'Mix oats, milk and whey the night before. Top with banana and peanut butter in the morning.',
      ing: [['Porridge oats',80,'g'],['Semi-skimmed milk',250,'ml'],['Whey protein',30,'g'],['Peanut butter',20,'g'],['Banana',1,'x'],['Honey',15,'g']]
    },
    b_scramble: {
      name: 'Scrambled eggs & bagel', type: 'breakfast', kcal: 610, p: 37, c: 42, f: 33,
      note: 'Soft-scramble 4 eggs in the butter, wilt the spinach through, pile onto a toasted cheesy bagel.',
      ing: [['Eggs',4,'x'],['Bagels',1,'x'],['Mature cheddar',30,'g'],['Spinach',40,'g'],['Butter',10,'g']]
    },
    b_yog: {
      name: 'Greek yogurt power bowl', type: 'breakfast', kcal: 600, p: 40, c: 56, f: 24,
      note: 'Stir the whey into the yogurt for extra protein, then layer granola, berries and nuts.',
      ing: [['Greek yogurt',200,'g'],['Granola',60,'g'],['Blueberries',80,'g'],['Honey',15,'g'],['Mixed nuts',25,'g'],['Whey protein',20,'g']]
    },

    // ── Lunch ──
    l_cnr: {
      name: 'Chicken & rice power bowl', type: 'lunch', kcal: 710, p: 56, c: 82, f: 14,
      note: 'The classic. Grill the chicken, pan the peppers and sweetcorn, serve over basmati.',
      ing: [['Chicken breast',200,'g'],['Basmati rice',90,'g'],['Olive oil',10,'ml'],['Mixed peppers',100,'g'],['Sweetcorn',80,'g']]
    },
    l_chilli: {
      name: 'Beef & bean chilli', type: 'lunch', kcal: 720, p: 47, c: 80, f: 17, batch: 'Batch cook — makes 4',
      note: 'Brown the mince with onion and peppers, add beans and tomatoes, simmer 30 min. Portion over rice.',
      ing: [['Beef mince 5%',150,'g'],['Red kidney beans',100,'g'],['Chopped tomatoes',100,'g'],['Basmati rice',90,'g'],['Onion',0.25,'x'],['Mixed peppers',30,'g']]
    },
    l_tuna: {
      name: 'Tuna pasta bake', type: 'lunch', kcal: 690, p: 46, c: 78, f: 22,
      note: 'Fold tuna, sweetcorn and creme fraiche through cooked pasta, top with cheddar, bake till golden.',
      ing: [['Tinned tuna',120,'g'],['Pasta',90,'g'],['Sweetcorn',60,'g'],['Mature cheddar',40,'g'],['Reduced-fat creme fraiche',40,'g']]
    },
    l_steak: {
      name: 'Steak & sweet potato', type: 'lunch', kcal: 650, p: 50, c: 48, f: 26,
      note: 'Roast sweet potato wedges, sear the steak 3 min a side, rest it, serve with tenderstem.',
      ing: [['Rump steak',200,'g'],['Sweet potato',250,'g'],['Tenderstem broccoli',100,'g'],['Olive oil',10,'ml']]
    },

    // ── Dinner ──
    d_salmon: {
      name: 'Salmon, potatoes & greens', type: 'dinner', kcal: 700, p: 42, c: 50, f: 34,
      note: 'Roast salmon and new potatoes 20 min, steam the tenderstem, finish with a squeeze of lemon.',
      ing: [['Salmon fillet',1,'x'],['New potatoes',250,'g'],['Tenderstem broccoli',100,'g'],['Olive oil',10,'ml']]
    },
    d_traybake: {
      name: 'Chicken thigh traybake', type: 'dinner', kcal: 800, p: 52, c: 58, f: 38,
      note: 'Everything on one tray — thighs, potatoes, peppers, red onion, olive oil. 35 min at 200°C.',
      ing: [['Chicken thighs',250,'g'],['Baby potatoes',250,'g'],['Mixed peppers',100,'g'],['Red onion',0.5,'x'],['Olive oil',15,'ml']]
    },
    d_bol: {
      name: 'High-protein spag bol', type: 'dinner', kcal: 760, p: 48, c: 86, f: 22, batch: 'Batch cook — makes 4',
      note: 'Lean mince, onion and tomatoes simmered down, finished with parmesan over spaghetti.',
      ing: [['Beef mince 5%',150,'g'],['Spaghetti',90,'g'],['Chopped tomatoes',100,'g'],['Onion',0.25,'x'],['Parmesan',15,'g'],['Olive oil',5,'ml']]
    },
    d_meatballs: {
      name: 'Turkey meatballs & pasta', type: 'dinner', kcal: 740, p: 56, c: 80, f: 18,
      note: 'Roll turkey mince with onion into meatballs, bake, simmer in passata, melt mozzarella on top.',
      ing: [['Turkey mince',150,'g'],['Pasta',90,'g'],['Passata',150,'g'],['Light mozzarella',60,'g'],['Onion',0.25,'x']]
    },
    d_pie: {
      name: 'Cottage pie', type: 'dinner', kcal: 690, p: 42, c: 62, f: 26, batch: 'Batch cook — makes 4',
      note: 'Mince with carrot, onion and gravy, topped with mash and a little cheddar, baked till crisp.',
      ing: [['Beef mince 5%',150,'g'],['Potatoes',250,'g'],['Carrots',60,'g'],['Onion',0.25,'x'],['Beef gravy',50,'ml'],['Mature cheddar',20,'g']]
    },

    // ── Snack ──
    s_shake: {
      name: 'Protein shake & PB toast', type: 'snack', kcal: 560, p: 44, c: 50, f: 22,
      note: 'Whey shaken with milk, plus two slices of wholemeal loaded with peanut butter.',
      ing: [['Whey protein',30,'g'],['Semi-skimmed milk',300,'ml'],['Wholemeal bread',2,'x'],['Peanut butter',25,'g']]
    },
    s_cottage: {
      name: 'Cottage cheese & rice cakes', type: 'snack', kcal: 360, p: 38, c: 30, f: 8,
      note: 'Rice cakes topped with cottage cheese and wafer-thin ham. Fast, lean and high protein.',
      ing: [['Cottage cheese',200,'g'],['Rice cakes',3,'x'],['Wafer thin ham',60,'g']]
    },
    s_trail: {
      name: 'Trail mix & milk', type: 'snack', kcal: 470, p: 18, c: 44, f: 26,
      note: 'A handful of nuts and raisins with a big glass of milk — easy calories between meals.',
      ing: [['Mixed nuts',40,'g'],['Raisins',30,'g'],['Semi-skimmed milk',300,'ml']]
    },
    s_yog: {
      name: 'Greek yogurt, honey & almonds', type: 'snack', kcal: 380, p: 22, c: 26, f: 20,
      note: 'Greek yogurt with a drizzle of honey and a scatter of almonds. Good before bed.',
      ing: [['Greek yogurt',200,'g'],['Honey',15,'g'],['Almonds',25,'g']]
    }
  };

  var SLOTS = [
    { key: 'breakfast', label: 'Breakfast' },
    { key: 'lunch',     label: 'Lunch' },
    { key: 'dinner',    label: 'Dinner' },
    { key: 'snack',     label: 'Snack' }
  ];
  var DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // Auto-plan rotations (kept varied and batch-friendly)
  var ROTA = {
    breakfast: ['b_oats', 'b_scramble', 'b_yog'],
    lunch:     ['l_cnr', 'l_chilli', 'l_tuna', 'l_steak'],
    dinner:    ['d_salmon', 'd_traybake', 'd_bol', 'd_meatballs', 'd_pie'],
    snack:     ['s_shake', 's_cottage', 's_trail', 's_yog']
  };

  // ── Shared pure helpers ──
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function catOf(item) { return CAT[item] || 'Food Cupboard'; }

  function fmtQty(qty, unit) {
    if (unit === 'x') return '×' + Math.ceil(qty - 1e-6);
    return Math.round(qty) + ' ' + unit;
  }

  // A meal id is either a library recipe or a custom (logged) meal.
  function mealById(id, customMeals) {
    if (!id) return null;
    if (RECIPES[id]) return RECIPES[id];
    if (customMeals && customMeals[id]) return customMeals[id];
    return null;
  }

  // Aggregate every ingredient across the planned week into one map,
  // keyed by "item|unit", combining duplicates. Logged meals carry no
  // ingredients, so they never reach the shopping list.
  function buildShoppingList(plan, customMeals) {
    var map = {};
    DAYS.forEach(function (d) {
      var slots = plan[d] || {};
      SLOTS.forEach(function (s) {
        var r = mealById(slots[s.key], customMeals);
        if (!r || !r.ing || !r.ing.length) return;
        r.ing.forEach(function (ing) {
          var key = ing[0] + '|' + ing[2];
          if (!map[key]) map[key] = { item: ing[0], unit: ing[2], qty: 0, cat: catOf(ing[0]) };
          map[key].qty += ing[1];
        });
      });
    });
    return map;
  }

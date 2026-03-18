// M5Paper S3 wall holder - step 2 (+ thumbtack recesses)
// Units: mm

$fn = 128;

// --- Outer block ---
outer_w = 131.5;  // width  (x)
outer_d = 17.7;   // depth  (y)
outer_h = 55.0;   // height (z)

// --- Inner cutout (x/z size) ---
cut_w = 121.5;    // width
cut_h = 50.0;     // height

// Cutout center position from the outer block origin (x/z)
cut_cx = 65.75;
cut_cz = 32.5;

// --- Make front fully open ---
back_wall = 7.0;     // keep back wall thickness
eps_front = 0.2;     // punch-through for robust boolean

cut_y0 = back_wall;
cut_y1 = outer_d + eps_front;
cut_d  = cut_y1 - cut_y0;

// --- Stopper pillars ---
stop_x = 5;
stop_y = 3;
stop_z = 20;

// Derived cutout bounds in x
cut_x0 = cut_cx - cut_w/2;   // = 5.0
cut_x1 = cut_cx + cut_w/2;   // = 126.5

// --- Thumbtack recesses (back side) ---
hole_diam  = 15;   // diameter
hole_r     = hole_diam/2;
hole_depth = 5;    // depth from back face (y=0) into +y
hole_dx    = 38;   // offset from center in x

difference() {
    union() {
        // Main body with front opening
        difference() {
            cube([outer_w, outer_d, outer_h], center=false);

            // Inner cutout (front fully open)
            translate([cut_cx - cut_w/2, cut_y0, cut_cz - cut_h/2])
                cube([cut_w, cut_d, cut_h], center=false);
        }

        // Left stopper (flush with opening plane)
        translate([cut_x0, outer_d - stop_y, 0])
            cube([stop_x, stop_y, stop_z], center=false);

        // Right stopper
        translate([cut_x1 - stop_x, outer_d - stop_y, 0])
            cube([stop_x, stop_y, stop_z], center=false);
    }

    // --- Subtract: 2 cylindrical recesses from inner face (y=back_wall) toward -y ---
    // Recess spans y = back_wall-hole_depth  ..  back_wall
    translate([outer_w/2 - hole_dx, back_wall, outer_h/2])
        rotate([90, 0, 0])  // cylinder axis along +y, so it will extend toward -y after rotation
            cylinder(h=hole_depth, r=hole_r, center=false);

    translate([outer_w/2 + hole_dx, back_wall, outer_h/2])
        rotate([90, 0, 0])
            cylinder(h=hole_depth, r=hole_r, center=false);
       // --- Through pin holes (Ø1.4mm) ---
    pin_diam  = 1.4;
    pin_r     = pin_diam/2;
    pin_depth = back_wall + 0.2;  // slight punch-through

    // Left pin hole
    translate([outer_w/2 - hole_dx, back_wall, outer_h/2])
        rotate([90, 0, 0])
            cylinder(h=pin_depth, r=pin_r, center=false);

    // Right pin hole
    translate([outer_w/2 + hole_dx, back_wall, outer_h/2])
        rotate([90, 0, 0])
            cylinder(h=pin_depth, r=pin_r, center=false);


}

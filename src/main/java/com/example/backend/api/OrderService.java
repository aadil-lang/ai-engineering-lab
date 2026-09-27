
// Patched:
@@ -123,7 +123,11 @@
     public void processOrder(Order order) {
-        // Code causing NullPointerException
+        if (order == null) {
+            throw new IllegalArgumentException("Order cannot be null");
+        }
+        // Continue with order processing logic
     }


import * as React from "react";

import {
  Badge,
  Button,
  Input,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Textarea,
} from "./index.js";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  DialogTrigger,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  SheetTrigger,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Toast,
  ToastDescription,
  ToastProvider,
  ToastTitle,
  ToastViewport,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "./primitives.js";

export default {
  title: "Design System/Primitives",
};

export function LightAndDark() {
  return (
    <TooltipProvider>
      <ToastProvider>
        <div className="ui-stack ui-stack-gap-4">
          <Button>Button</Button>
          <Input aria-label="Input" placeholder="Input" />
          <Textarea aria-label="Textarea" placeholder="Textarea" />
          <Select aria-label="Select" defaultValue="one">
            <option value="one">One</option>
            <option value="two">Two</option>
          </Select>
          <Badge tone="success">Badge</Badge>
          <Dialog>
            <DialogTrigger asChild>
              <Button tone="secondary">Dialog</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogTitle>Dialog title</DialogTitle>
              <DialogDescription>Dialog description</DialogDescription>
            </DialogContent>
          </Dialog>
          <Sheet>
            <SheetTrigger asChild>
              <Button tone="ghost">Sheet</Button>
            </SheetTrigger>
            <SheetContent>
              <SheetTitle>Sheet title</SheetTitle>
              <SheetDescription>Sheet description</SheetDescription>
            </SheetContent>
          </Sheet>
          <Tabs defaultValue="one">
            <TabsList>
              <TabsTrigger value="one">One</TabsTrigger>
              <TabsTrigger value="two">Two</TabsTrigger>
            </TabsList>
            <TabsContent value="one">Panel one</TabsContent>
            <TabsContent value="two">Panel two</TabsContent>
          </Tabs>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button tone="ghost">Tooltip</Button>
            </TooltipTrigger>
            <TooltipContent>Tooltip content</TooltipContent>
          </Tooltip>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Column</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell>Cell</TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <Toast open>
            <ToastTitle>Toast title</ToastTitle>
            <ToastDescription>Toast description</ToastDescription>
          </Toast>
          <ToastViewport />
        </div>
      </ToastProvider>
    </TooltipProvider>
  );
}
